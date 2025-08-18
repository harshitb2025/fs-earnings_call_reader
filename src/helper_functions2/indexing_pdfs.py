import os
from mistralai import Mistral, async_client
import httpx
import base64
import io
import tempfile
import asyncio
import certifi


def temporary_file_path(uploaded_file):
   
    # Step 1: Save the uploaded file temporarily
    tmp_file_path=None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name
    
    return tmp_file_path
  

def async_mistral_client(api_key):
    # async_client_instance = httpx.AsyncClient()

    # Initialize the Mistral client
    mistral_async_client = Mistral(api_key=api_key,async_client=httpx.AsyncClient(verify=certifi.where()))
    return mistral_async_client

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


# async def mistral_signed_pdf_url(pdf_path: str, api_key: str):
#     client = async_mistral_client(api_key)

#     with aiofiles.open(pdf_path, "rb") as f:
#         content = f.read()

#     uploaded_pdf = await client.files.upload(
#         file={
#             "file_name": pdf_path,
#             "content": content,
#         },
#         purpose="ocr"
#     )

#     await client.files.retrieve(file_id=uploaded_pdf.id)  # Optional if not needed
#     signed_url = await client.files.get_signed_url(file_id=uploaded_pdf.id)

#     return client, signed_url

def mistral_ocr_pdf(pdf_path:str, api_key):
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


def mistral_ocr_pdf_streamlit(uploaded_file, api_key):
    """
    Saves the uploaded file temporarily, performs OCR using Mistral, and then deletes the temp file.

    Args:
        uploaded_file: File uploaded via Streamlit (from st.file_uploader).
        api_key: API key for Mistral.

    Returns:
        OCR response from Mistral.
    """
    save_dir=r"C:\Users\73335\Downloads"
   
    # Step 1: Save the uploaded file temporarily
    tmp_file_path=None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=save_dir) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name
        print(tmp_file_path)
  


    try:
        # Step 2: Pass the temp file path to the existing OCR logic
        client, signed_url = mistral_signed_pdf_url(pdf_path=tmp_file_path, api_key=api_key)
        print(signed_url)

        if not signed_url:
            return {"error": "Failed to generate signed URL"}
        

        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url,
            }, 
            include_image_base64=True
        )

        os.remove(tmp_file_path)

        return tmp_file_path,ocr_response
    
    except:
        return "Error in generating OCR response"

