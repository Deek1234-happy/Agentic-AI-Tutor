# app/parsers.py
import fitz
import pytesseract
from PIL import Image
from docx import Document
from docx.oxml.ns import qn
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import io
import os


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# OCR working implementation, but with no oreder between text and images at the same page
def parse_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    final_text = []

    for page_number, page in enumerate(doc, start=1):
        final_text.append(f"\n--- Page {page_number} ---\n")

        text = page.get_text().strip()
        if text:
            final_text.append(text + "\n")

        images = page.get_images(full=True)

        # Case 1: scanned page (almost no text)
        if len(text) < 100:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
            ocr_text = pytesseract.image_to_string(img)

            if ocr_text.strip():
                final_text.append("\n[OCR PAGE TEXT]\n")
                final_text.append(ocr_text + "\n")

        # Case 2: normal page with small images
        elif images:
            for img_info in images:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                img = Image.open(io.BytesIO(image_bytes)).convert("L")
                ocr_text = pytesseract.image_to_string(img)

                if ocr_text.strip():
                    final_text.append("\n[OCR IMAGE TEXT]\n")
                    final_text.append(ocr_text + "\n")

    return "".join(final_text)

def parse_docx(file_path: str) -> str:
    document = Document(file_path)
    final_text = []

    # Map relationship id → image bytes
    rels = document.part.rels

    for element in document.element.body:

        # Paragraph
        if element.tag.endswith('}p'):
            paragraph_text = []

            for run in element.iter(qn('w:r')):
                text_elem = run.find(qn('w:t'))
                if text_elem is not None and text_elem.text:
                    paragraph_text.append(text_elem.text)

                # Image inside paragraph → OCR
                drawing = run.find(qn('w:drawing'))
                if drawing is not None:
                    for blip in drawing.iter(qn('a:blip')):
                        rId = blip.get(qn('r:embed'))
                        image_part = rels[rId]
                        image_bytes = image_part.target_part.blob

                        img = Image.open(io.BytesIO(image_bytes)).convert("L")
                        ocr_text = pytesseract.image_to_string(img)

                        if ocr_text.strip():
                            paragraph_text.append("\n" + ocr_text + "\n")

            if paragraph_text:
                final_text.append("".join(paragraph_text) + "\n")

        # Table 
        elif element.tag.endswith('}tbl'):
            table = document.tables.pop(0)
            for row in table.rows:
                for cell in row.cells:
                    final_text.append(cell.text + " ")
                final_text.append("\n")

    return "".join(final_text)


def parse_pptx(file_path: str) -> str:
    presentation = Presentation(file_path)
    final_text = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        final_text.append(f"\n--- Slide {slide_number} ---\n")

        for shape in slide.shapes:

            # TEXT SHAPES
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text.strip():
                        final_text.append(paragraph.text + "\n")

            # IMAGE SHAPES → OCR
            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image_bytes = shape.image.blob
                img = Image.open(io.BytesIO(image_bytes)).convert("L")

                ocr_text = pytesseract.image_to_string(img)

                if ocr_text.strip():
                    final_text.append("\n[OCR IMAGE TEXT]\n")
                    final_text.append(ocr_text + "\n")

    return "".join(final_text)


def parse_txt(file_path: str) -> str:
    try:
        # UTF-8 encoding
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    except UnicodeDecodeError:
        # Fallback for other encodings
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


import csv


def parse_csv(file_path: str) -> str:
    lines = []

    # UTF-8 encoding
    try:
        file = open(file_path, newline="", encoding="utf-8")
    except UnicodeDecodeError:
        file = open(file_path, newline="", encoding="latin-1")

    with file:
        reader = csv.reader(file)

        for row in reader:
            # Skip empty rows
            if not row:
                continue

            # Join columns into readable text
            line = " | ".join(cell.strip() for cell in row if cell.strip())
            if line:
                lines.append(line)

    return "\n".join(lines)