import fitz  # PyMuPDF
import os
import easyocr

zoom = 4.167 
matrix = fitz.Matrix(zoom, zoom)
reader = easyocr.Reader(['en'], gpu=False)

def extract_text_from_pdf(pdf):
    # Open the PDF file
    pdf = fitz.open(stream=pdf, filetype="pdf")
    text = ""

    # Iterate through each page
    for page in pdf:
        page_img = page.get_pixmap(matrix=matrix, colorspace="GRAY")  # Render page to an image
        page_img = page_img.tobytes("ppm")  # Convert to bytes
        text += reader.readtext(page_img)
    return text


def chunking_text(text, chunk_size=1000, overlap=200):
    # Split the text into chunks of specified size
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks