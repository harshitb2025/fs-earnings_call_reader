import pdfplumber
import os
from src.helper_functions2.extracting_images2 import base64_to_image_content
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import base64
import numpy as np



def split_pages(aggregated_markdown:str):
    # Match page markers like <start_of_page_1>, <start_of_page_2>, etc.
    pattern = r"<start_of_page_(\d+)>"
    
    # Split the string at each page marker and keep the markers
    parts = re.split(pattern, aggregated_markdown)
    
    # The first part (parts[0]) is the content before the first marker, usually empty or irrelevant
    pages = {}
    for i in range(1, len(parts) - 1, 2):
        page_number = int(parts[i])
        page_content = parts[i + 1].strip()
        pages[page_number] = page_content
    
    return pages

def replace_images_with_content(prompt,api_key,input_text, base64_img_list):
    """
    Replaces markdown-style image references with Base64-encoded images.
    
    Args:
        input_text (str): Markdown content containing image references.
        base64_images (list): A list of Base64-encoded image strings in order.
    
    Returns:
        str: Modified markdown content with Base64 images embedded.
    """
    
    # Regex pattern to find image markdown format
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    
    # Iterator for Base64 images to maintain order
    base64_iterator = iter(base64_img_list)
    img_index=iter(list(np.arange(0,len(base64_img_list))))
    
    def replacer(match):
        """Replace markdown image reference with its Base64-encoded counterpart."""
        try:
            base64_img = next(base64_iterator)  # Get the next Base64 string
            img_index2=next(img_index)
            return f"\n IMAGE {img_index2+1} begins..\n " +base64_to_image_content(prompt=prompt,base64_encoding=base64_img,api_key=api_key)+  f"\n IMAGE {img_index2+1} ends.. \n"
        except StopIteration:
            return match.group(0)  # If images run out, return original markdown
    
    # Replace markdown image syntax with Base64 images
    modified_text = image_pattern.sub(replacer, input_text)
    
    return modified_text


def threaded_replace_images_with_content(prompt, api_key, input_text, base64_img_list, max_workers=7):
    """
    Replaces markdown-style image references with Base64-encoded content using threading.
    
    Args:
        prompt (str): Prompt to be passed to image content generator.
        api_key (str): API key for image content generation.
        input_text (str): Markdown content with image references.
        base64_img_list (list): List of Base64 image strings.
        max_workers (int): Number of threads to use.
    
    Returns:
        str: Markdown with embedded image content.
    """
    
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    matches = list(image_pattern.finditer(input_text))

    def process_image(index, base64_img):
        content = base64_to_image_content(prompt=prompt, base64_encoding=base64_img, api_key=api_key)
        return index, f"\n IMAGE {index + 1} begins..\n {content}\n IMAGE {index + 1} ends.. \n"

    replacements = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(process_image, i, base64_img): i
            for i, base64_img in enumerate(base64_img_list[:len(matches)])
        }

        for future in as_completed(future_to_index):
            idx, result = future.result()
            replacements[idx] = result

    # Reconstruct the markdown with replacements
    def replacer(match):
        nonlocal match_index
        result = replacements.get(match_index, match.group(0))
        match_index += 1
        return result

    match_index = 0
    modified_text = image_pattern.sub(replacer, input_text)

    return modified_text


def aggregate_markdowns(ocr_response):
    markdowns=""
    for docu in ocr_response.pages:
        markdowns+=f"\n<start_of_page_{str(docu.index+1)}>\n"
        markdowns+=docu.markdown
        markdowns+=f"\n<end_of_page_{str(docu.index+1)}>\n"
        
    return markdowns
def markdown_per_page(ocr_response,page_no):
    return ocr_response.pages[page_no-1].markdown


def save_markdowns(pdf_path, markdown_content):
    # Create directory if it does not exist
    markdown_dir = "pdf_markdowns"
    os.makedirs(markdown_dir, exist_ok=True)

    # Extract filename from PDF path (without extension)
    pdf_filename = os.path.basename(pdf_path)
    markdown_filename = os.path.splitext(pdf_filename)[0] + ".md"  # Change .pdf to .md

    # Full path to save markdown file
    markdown_path = os.path.join(markdown_dir, markdown_filename)

    # Save the markdown content
    with open(markdown_path, "w", encoding="utf-8") as file:
        file.write(markdown_content)

    print(f"Markdown saved: {markdown_path}")


### LEGACY CODE FOR EXTRACTING CONTENT FROM PDFs
def extract_text_from_pdf(pdf_file):
    text=""
    with pdfplumber.open(pdf_file) as reader:
        for pageno, page in enumerate(reader.pages):
            text+="start_of_page_"+str(pageno)
            text += page.extract_text() + "\n"
            text+="end_of_page_"  +str(pageno)
                    # pdf_content[pageno]=text
        return text




