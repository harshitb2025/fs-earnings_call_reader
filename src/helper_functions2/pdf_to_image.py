import base64
import io
from io import BytesIO
from PIL import Image
import io
import pymupdf

def pdf_to_images_in_list2(uploaded_file):    #THIS IS FOR STREAMLIT UPLOADED PDF

    """
    Convert each page of an uploaded PDF into an image and return them as a list of PIL Image objects.

    :param uploaded_file: Streamlit uploaded file object
    :return: List of PIL Image objects
    """
    images = []
    
    # Open the PDF file from the uploaded file stream
    pdf_document = pymupdf.open(stream=uploaded_file.read(), filetype="pdf")
    
    # Iterate through each page
    for page_number in range(len(pdf_document)):
        # Get the page as a pixmap (image)
        pix = pdf_document[page_number].get_pixmap()
        
        # Convert pixmap to a bytes object (PNG format)
        img_bytes = pix.tobytes("png")
        
        # Open the image with PIL
        image = Image.open(io.BytesIO(img_bytes))
        
        # Append the PIL Image to the list
        images.append(image)
    
    return images



def pdf_to_images_in_list(pdf_path):
    """
    Convert each page of a PDF into an image and return them as a list of PIL Image objects.

    :param pdf_path: Path to the input PDF file
    :return: List of PIL Image objects
    """
    images = []
    
    # Open the PDF file
    pdf_document = pymupdf.open(pdf_path)
    
    # Iterate through each page
    for page_number in range(len(pdf_document)):
        # Get the page
        page = pdf_document.load_page(page_number)
        
        # Get the page as a pixmap (image)
        pix = page.get_pixmap(dpi=200)
        
        # Convert pixmap to a bytes object (PNG format)
        img_bytes = pix.tobytes("png")
        
        # Open the image with PIL
        image = Image.open(io.BytesIO(img_bytes))
        
        # Append the PIL Image to the list
        images.append(image)
    
    # Close the document
    pdf_document.close()
    
    return images



def pil_to_base64(image: Image.Image, format="PNG") -> str:
    """Converts a PIL Image to a Base64 encoded string without saving it."""
    buffered = BytesIO()
    image.save(buffered, format=format)  # Convert the image to bytes
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")  # Encode to Base64
    return img_str