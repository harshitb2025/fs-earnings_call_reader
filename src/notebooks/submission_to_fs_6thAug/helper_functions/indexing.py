from mistralai import Mistral
import os
import httpx
import asyncio

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



async def process_multiple_pdfs(pdf_paths: list, api_key: str):
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

