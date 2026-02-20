# app/router.py
import os
from .parsers import (
    parse_pdf,
    parse_docx,
    parse_pptx,
    parse_txt,
    parse_csv
)

SUPPORTED_TYPES = ["pdf", "docx", "pptx", "txt", "csv"]

def validate_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError("File does not exist")

def validate_file_type(file_type: str):
    if file_type.lower() not in SUPPORTED_TYPES:
        raise ValueError("Unsupported file type")

def route_file(file_path: str, file_type: str):
    file_type = file_type.lower()

    if file_type == "pdf":
        return parse_pdf(file_path)

    if file_type == "docx":
        return parse_docx(file_path)

    if file_type == "pptx":
        return parse_pptx(file_path)

    if file_type == "txt":
        return parse_txt(file_path)

    if file_type == "csv":
        return parse_csv(file_path)

    raise ValueError("No parser found")