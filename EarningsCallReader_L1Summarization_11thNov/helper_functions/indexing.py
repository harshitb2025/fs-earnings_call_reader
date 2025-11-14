import pandas as pd
import os
from mistralai import Mistral
import httpx
import re
from openai import OpenAI, AsyncOpenAI
import asyncio
import yaml


## NEWLY ADDED FUNCTIONS

def reading_yaml(file_name):
    current_dir = os.path.dirname(__file__)

    # Build path to prompts.yaml
    yaml_file = os.path.join(current_dir, file_name)


    with open(yaml_file, 'r') as file:
        prompts = yaml.safe_load(file)

    return prompts

def openai_client(api_key):
    client = OpenAI(api_key=api_key)
    return client

def openai_message(text, base64_encoding):
     messages=[
        {
            "role": "user",
            "content": [
                { "type": "text", "text": text },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": base64_encoding,
                    },
                },
            ],
        }
    ]
     return messages


def mistral_client(api_key):
       client = Mistral(api_key=api_key, 
    client=httpx.Client(verify=False)
)
       return client

def mistral_signed_pdf_url(pdf_path:str, api_key):
    client=mistral_client(api_key=api_key)
    uploaded_pdf=client.files.upload(
    file={
        "file_name": pdf_path,
        "content": open(pdf_path, "rb"),
    },
    purpose="ocr"
)
    client.files.retrieve(file_id=uploaded_pdf.id)
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    return client,signed_url


def base_64_list_per_page(ocr_response,page_no):   
    """
    Gets base64 encodings of images per page, all the images are in the same order as they are in the page
    """
    base64_strings=[]
    base64_for_gpt=[]
    for image in ocr_response.pages[page_no-1].images:
        base64_for_gpt.append(image.image_base64)
        base64_img=image.image_base64.split(',')[1]
        base64_strings.append(base64_img)
    return base64_strings, base64_for_gpt

def base_64_list_all_pages(ocr_response):
    """
    Gets base64 encodings of all images present in the PDF in form of list and all the images are in the order.
    """
    base_64_all=[]
    total_no_of_pages=len(ocr_response.pages)
    for page in range(1, total_no_of_pages+1):
        a,b=base_64_list_per_page(ocr_response=ocr_response,page_no=page)
        base_64_all.extend(b)
    return base_64_all

async def base64_to_image_content(prompt, base64_encoding, api_key):
    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": base64_encoding }}
                ]
            }
        ],
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

async def process_all_images(prompt, api_key, base64_img_list):
    """
    Asynchronously processes all Base64 images using OpenAI API and returns the generated contents.
    """
    tasks = [
        base64_to_image_content(prompt=prompt, base64_encoding=img, api_key=api_key)
        for img in base64_img_list
    ]
    return await asyncio.gather(*tasks)

def replace_markdown_images_with_content(input_text, generated_contents):
    
    if not isinstance(input_text, str):
        raise ValueError("Expected 'input_text' to be a string, got None or invalid type.")

    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    content_iter = iter(generated_contents)
    index = 1

    def replacer(match):
        nonlocal index
        try:
            content = next(content_iter)
            result = f"\nIMAGE {index} begins...\n{content}\nIMAGE {index} ends...\n"
            index += 1
            return result
        except StopIteration:
            return match.group(0)

    return image_pattern.sub(replacer, input_text)

def mistral_ocr_pdf(pdf_path:str, api_key):
    client=mistral_client(api_key=api_key)
    if pdf_path.startswith('https://'):
        ocr_response = client.ocr.process( model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": pdf_path,
        }, 
        include_image_base64=True
    )
        
    else:
        client,signed_url=mistral_signed_pdf_url(pdf_path=pdf_path, api_key=api_key)
        ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        }, 
        include_image_base64=True
    )
    return ocr_response

async def amistral_ocr_pdf(pdf_path: str, api_key: str):
    client, signed_url = mistral_signed_pdf_url(pdf_path, api_key)

    ocr_response = await client.ocr.process_async(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
        include_image_base64=True
    )

    return ocr_response
    
def aggregate_markdowns(ocr_response):  
    markdowns=""
    for docu in ocr_response.pages:
        markdowns+=f"\n<start_of_page_{str(docu.index+1)}>\n"
        markdowns+=docu.markdown
        markdowns+=f"\n<end_of_page_{str(docu.index+1)}>\n"
    return markdowns

def save_markdown_to_file(markdown_content, output_file):
    """
    Saves the markdown content to a specified file.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"✅ Markdown content saved to {output_file}")

async def process_multiple_pdfs(pdf_paths: list, api_key: str, replace_images: bool = True, prompt="Extract all the text from the image"):
    tasks = {
        asyncio.create_task(amistral_ocr_pdf(path, api_key)): path
        for path in pdf_paths
    }

    results = {}  # Dictionary to hold PDF path → result
    pending_pdfs = set(pdf_paths)

    for completed_task in list(tasks.keys()):
        try:
            result = await completed_task
            pdf_path = tasks[completed_task]
            print(f"✅ Finished processing: {pdf_path}")
            pdf_content= aggregate_markdowns(result)
            if replace_images:
                generated_contents = await process_all_images(
                    prompt=prompt,
                    api_key=os.environ.get("OPENAI_API_KEY"),
                    base64_img_list=base_64_list_all_pages(result)
                )
                results[pdf_path] = replace_markdown_images_with_content(input_text=pdf_content,generated_contents=generated_contents)
            else:
                results[pdf_path] = pdf_content

            os.makedirs("pdf_markdowns", exist_ok=True)
            file_name=os.path.basename(pdf_path)[:-4]
            save_markdown_to_file(markdown_content=results[pdf_path], output_file=f"pdf_markdowns/{file_name}.md")

        
        except Exception as e:
            pdf_path = tasks.get(completed_task, "<unknown>")
            print(f"❌ Error processing {pdf_path}: {e}")
            results[pdf_path] = None

        pending_pdfs.discard(pdf_path)
        if pending_pdfs:
            print(f"⏳ Still waiting on: {', '.join(pending_pdfs)}")

    return results



### LEGACY FUNCTIONS

def get_mistral_client(mistral_api_key):
    return Mistral(api_key=mistral_api_key, client=httpx.Client(verify=False))

def upload_pdf(pdf_path,mistral_api_key):
    """
    Uploads a PDF file to the Mistral API for OCR processing.
    """
    client = get_mistral_client(mistral_api_key)
    uploaded_pdf = client.files.upload(
        file={
            "file_name": os.path.basename(pdf_path),
            "content": open(pdf_path, "rb"),
        },
        purpose="ocr"
    )  
    return uploaded_pdf

def retrieve_pdf(uploaded_pdf,mistral_api_key):
    """
    Retrieves a PDF file from the Mistral API.
    """
    client = get_mistral_client(mistral_api_key)
    # retrieved_pdf=client.files.retrieve(file_id=uploaded_pdf.id)
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    return signed_url.url

def markdown_from_url(url,mistral_api_key):
    """
    Returns markdown content from a URL.
    """         
    client = get_mistral_client(mistral_api_key=mistral_api_key)
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": url
        },
        include_image_base64=False,
    )
    return ocr_response
def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """
    Replaces image in a markdown string with base64-encoded images.
    """
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})")
    return markdown_str


def get_combined_markdown(ocr_response):
  """
  Combines the markdown content from multiple pages into a single markdown string.
  """

  markdowns= []
  for page in ocr_response.pages:
    image_data = {}
    for img in page.images:
      image_data[img.id] = img.image_base64
    markdowns.append(replace_images_in_markdown(page.markdown, image_data))
    
  return "\n\n".join(markdowns)


def pdf_to_markdown(pdf_path,mistral_api_key):

    if pdf_path.startswith('https://'):
        ocr_response = markdown_from_url(url=pdf_path)
        markdown_text = get_combined_markdown(ocr_response)
        return(markdown_text)
    else:
        uploaded_pdf=upload_pdf(pdf_path=pdf_path,mistral_api_key=mistral_api_key)
        signed_pdf_url=retrieve_pdf(uploaded_pdf,mistral_api_key)
        ocr_response = markdown_from_url(signed_pdf_url,mistral_api_key)
        markdown_text = get_combined_markdown(ocr_response)
        return(markdown_text)
    
async def pdf_to_markdown(pdf_path, mistral_api_key, replace_images=True, prompt="Extract all the text from the image"):
    """
    Converts a PDF file to markdown using Mistral OCR.
    
    Parameters:
        pdf_path (str): The path to the PDF file or a URL.
        mistral_api_key (str): The Mistral API key.
        
    Returns:
        str: The markdown content extracted from the PDF.
    """

    ocr_response = mistral_ocr_pdf(pdf_path=pdf_path, api_key=mistral_api_key)
    markdown_text = aggregate_markdowns(ocr_response)
    print("✅ Markdown text extracted from the PDF")
    
    if replace_images:
        generated_contents = await process_all_images(
        prompt=prompt,
        api_key=os.environ.get("OPENAI_API_KEY"),
        base64_img_list=base_64_list_all_pages(ocr_response)
    )
        print("✅ Image content extracted and replaced in markdown")
        
        markdown_text=replace_markdown_images_with_content(input_text=markdown_text,generated_contents=generated_contents)

    os.makedirs("pdf_markdowns", exist_ok=True)
    file_name=os.path.basename(pdf_path)[:-4]
    save_markdown_to_file(markdown_content=markdown_text, output_file=f"pdf_markdowns/{file_name}.md")
    return markdown_text
