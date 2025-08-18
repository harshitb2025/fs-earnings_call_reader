import pandas as pd
import os
from mistralai import Mistral
import httpx
import re
from mistralai.models import OCRResponse
from IPython.display import Markdown, display
from openai import OpenAI
import yaml

def markdown_from_url(url,mistral_api_key):
    """
    Returns markdown content from a URL.
    """         
    client = Mistral(api_key=mistral_api_key,client=httpx.Client(verify=False))

    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": url
        },
        include_image_base64=False,
    )
    return ocr_response

def upload_pdf(pdf_path,mistral_api_key):
    """
    Uploads a PDF file to the Mistral API for OCR processing.
    """
    client = Mistral(api_key=mistral_api_key,client=httpx.Client(verify=False))
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
    client = Mistral(api_key=mistral_api_key,client=httpx.Client(verify=False))
    # retrieved_pdf=client.files.retrieve(file_id=uploaded_pdf.id)
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    return signed_url.url


def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """
    Replaces image in a markdown string with base64-encoded images.
    """
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})")
    return markdown_str

def get_base64_images(ocr_response: OCRResponse) -> dict:
    """
    Returns a dictionary of image base64 strings from an OCR response.
    """
    image_data = {}
    for page in ocr_response.pages:
        for img in page.images:
            image_data[img.id] = img.image_base64
    return image_data

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    """
    Combines the markdown content from multiple pages into a single markdown string.
    """
    markdowns: list[str] = []
    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            image_data[img.id] = img.image_base64
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))


    # return "\n\n".join(markdowns)

    aggregate_markdown=""
    for page_no, markdown in enumerate(markdowns, start=1):
        aggregate_markdown += (
            f"\n\n<START_OF_PAGE_{page_no}>\n\n"
            f"{markdown.strip()}\n\n"
            f"<END_OF_PAGE_{page_no}>\n\n"
        )

    return aggregate_markdown





def image_to_text(base64_image,openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                { "type": "text", "text": "what's in this image? Extract all the information in json format" },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": base64_image,
                    },
                },
            ],
        }
    ],
    response_format={"type": "json_object"},
)

    return(completion.choices[0].message.content)



def replace_base64_with_text(markdown_text, image_text_mapping):
    """
    Replaces base64-encoded images in the markdown text with extracted text.
    
    Parameters:
        markdown_text (str): The markdown text containing base64-encoded images.
        image_text_mapping (dict): A dictionary mapping base64 strings (or part of it) to extracted text.
        
    Returns:
        str: The updated markdown text with base64 images replaced by extracted text.
    """
    
    def replace_match(match):
        base64_str = match.group(1)  # Taking only the first 30 characters for mapping
        extracted_text = image_text_mapping.get(base64_str, list(image_text_mapping.values())[0])
        return f"\n #Infromation extracted from Image : \n{extracted_text}\n"
    
    # Regex to match base64-encoded images
    base64_pattern = re.compile(r'!\[.*?\]\(data:image\/jpeg;base64,(.*?)\)')
    
    return re.sub(base64_pattern, replace_match, markdown_text)

def load_yaml(file_path):
    try:
        with open(file_path,'r',encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
