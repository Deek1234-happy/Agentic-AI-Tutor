# app/parsers.py
"""
Document parsers for the RAG pipeline.
Upgraded to match the Quiz parser quality:
  - use_ocr flag on every parser (default True)
  - PDF: skips tiny images (< 50 px) to avoid garbage OCR
  - DOCX: table lookup by element identity (no .pop(0) race condition)
  - PPTX: OCR guarded by use_ocr flag
"""

import fitz
import pytesseract
from PIL import Image
from docx import Document
from docx.oxml.ns import qn
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import csv
import io
import os


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ─────────────────────────────────────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────────────────────────────────────

def parse_pdf(file_path: str, use_ocr: bool = True) -> str:
    doc = fitz.open(file_path)
    final_text = []

    for page_number, page in enumerate(doc, start=1):
        final_text.append(f"\n--- Page {page_number} ---\n")

        text = page.get_text().strip()
        if text:
            final_text.append(text + "\n")

        if not use_ocr:
            continue

        images = page.get_images(full=True)

        # Case 1: scanned page (almost no selectable text)
        if len(text) < 100:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text.strip():
                final_text.append("\n[OCR PAGE TEXT]\n")
                final_text.append(ocr_text + "\n")

        # Case 2: normal page with embedded images (and not much text yet)
        elif images and len(text) < 300:
            for img_info in images:
                base_image = doc.extract_image(img_info[0])

                # Skip tiny decorative images
                if base_image["width"] < 50 or base_image["height"] < 50:
                    continue

                img = Image.open(io.BytesIO(base_image["image"])).convert("L")
                ocr_text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")

                if len(ocr_text.split()) > 5:
                    final_text.append("\n[OCR IMAGE TEXT]\n")
                    final_text.append(ocr_text + "\n")

    return "".join(final_text)


# ─────────────────────────────────────────────────────────────────────────────
# DOCX
# ─────────────────────────────────────────────────────────────────────────────

def parse_docx(file_path: str, use_ocr: bool = True) -> str:
    document = Document(file_path)
    final_text = []

    rels = document.part.rels
    # Build lookup by element identity — avoids the .pop(0) ordering bug
    table_lookup = {id(tbl._element): tbl for tbl in document.tables}

    for element in document.element.body:

        # ── Paragraph ───────────────────────────────────────────────────────
        if element.tag.endswith("}p"):
            paragraph_text = []

            for run in element.iter(qn("w:r")):
                text_elem = run.find(qn("w:t"))
                if text_elem is not None and text_elem.text:
                    paragraph_text.append(text_elem.text)

                if use_ocr:
                    drawing = run.find(qn("w:drawing"))
                    if drawing is not None:
                        for blip in drawing.iter(qn("a:blip")):
                            rId = blip.get(qn("r:embed"))
                            image_part = rels[rId]
                            image_bytes = image_part.target_part.blob
                            img = Image.open(io.BytesIO(image_bytes)).convert("L")
                            ocr_text = pytesseract.image_to_string(img)
                            if ocr_text.strip():
                                paragraph_text.append("\n" + ocr_text + "\n")

            if paragraph_text:
                final_text.append("".join(paragraph_text) + "\n")

        # ── Table ────────────────────────────────────────────────────────────
        elif element.tag.endswith("}tbl"):
            table = table_lookup.get(id(element))
            if table is None:
                continue
            for row in table.rows:
                for cell in row.cells:
                    final_text.append(cell.text + " ")
                final_text.append("\n")

    return "".join(final_text)


# ─────────────────────────────────────────────────────────────────────────────
# PPTX
# ─────────────────────────────────────────────────────────────────────────────

def parse_pptx(file_path: str, use_ocr: bool = True) -> str:
    presentation = Presentation(file_path)
    final_text = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        final_text.append(f"\n--- Slide {slide_number} ---\n")

        for shape in slide.shapes:

            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text.strip():
                        final_text.append(paragraph.text + "\n")

            elif use_ocr and shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image_bytes = shape.image.blob
                img = Image.open(io.BytesIO(image_bytes)).convert("L")
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text.strip():
                    final_text.append("\n[OCR IMAGE TEXT]\n")
                    final_text.append(ocr_text + "\n")

    return "".join(final_text)


# ─────────────────────────────────────────────────────────────────────────────
# TXT
# ─────────────────────────────────────────────────────────────────────────────

def parse_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────────────────────────────────────

def parse_csv(file_path: str) -> str:
    lines = []
    try:
        file = open(file_path, newline="", encoding="utf-8")
    except UnicodeDecodeError:
        file = open(file_path, newline="", encoding="latin-1")

    with file:
        reader = csv.reader(file)
        for row in reader:
            if not row:
                continue
            line = " | ".join(cell.strip() for cell in row if cell.strip())
            if line:
                lines.append(line)

    return "\n".join(lines)