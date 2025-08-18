import re
from openai import OpenAI
import os



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

def base64_to_image_content(prompt,base64_encoding, api_key,model_name="gpt-4o"):

    client_openai=openai_client(api_key=api_key)
    completion = client_openai.chat.completions.create(
    model=model_name,
    messages=openai_message(text=prompt, base64_encoding=base64_encoding)
    )
    
    return completion.choices[0].message.content



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

