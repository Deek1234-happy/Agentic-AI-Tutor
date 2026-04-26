# app/quiz.py
from fastapi import APIRouter, UploadFile, File, Query
import os
import json
from datetime import datetime

from .processor import process_document
from .router import SUPPORTED_TYPES

router = APIRouter()


def _progress(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [quiz.upload] {message}", flush=True)


@router.post("/process")
async def process_document_api(
    file: UploadFile = File(...),
    use_bart: bool = Query(default=False, description="Use BART for micro-header generation (slower, better quality). Defaults to False — headers are overwritten by Gemini in S3."),
    use_ocr: bool = Query(default=False, description="Run Tesseract OCR on embedded images. Defaults to false; turn it on only when you need OCR for image-heavy documents."),
    force_reprocess: bool = Query(default=True, description="Ignore cache and reprocess the file"),
):
    """
    Process a PDF/DOCX/PPTX/TXT file through the semantic chunking pipeline.

    Returns:
      - chunks_created: number of chunks after deduplication and filtering
      - output_file: path to the saved JSONL file
      - Each chunk in the JSONL contains:
          file_id, chunk_id, concept_heading, text, text_with_context,
          word_count, token_count, semantic_score, quality_score, micro_header
    """
    UPLOAD_DIR = "data/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    _progress(f"Received upload request for {file.filename or 'unknown file'}")

    # FIX: path traversal — strip any directory components from the filename.
    # Without this, a filename like "../../etc/passwd" would write outside
    # UPLOAD_DIR. os.path.basename() isolates the bare filename.
    safe_filename = os.path.basename(file.filename or "upload")
    if not safe_filename:
        _progress("Rejected upload because the filename was invalid")
        return {
            "message": "Failed — invalid filename",
            "chunks_created": 0,
            "output_file": None,
        }

    # FIX: validate file extension before writing to disk.
    # Rejects unsupported types immediately instead of letting route_file()
    # raise a ValueError after the file is already saved.
    file_type = safe_filename.rsplit(".", 1)[-1].lower() if "." in safe_filename else ""
    if file_type not in SUPPORTED_TYPES:
        _progress(f"Rejected {safe_filename} because file type '{file_type}' is not supported")
        return {
            "message": f"Failed — unsupported file type '{file_type}'. Supported: {SUPPORTED_TYPES}",
            "chunks_created": 0,
            "output_file": None,
        }

    temp_path = os.path.join(UPLOAD_DIR, safe_filename)

    _progress(f"Saving {safe_filename} to {temp_path}")

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    _progress(f"Starting document processing for {safe_filename}")

    try:
        output_file, count = process_document(
            temp_path,
            file_type,
            use_ocr=use_ocr,
            use_bart=use_bart,
            force_reprocess=force_reprocess,
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            _progress(f"Removed temporary upload {temp_path}")

    if output_file is None:
        _progress(f"Processing finished for {safe_filename} but no text could be extracted")
        return {
            "message": "Failed — no text could be extracted",
            "chunks_created": 0,
            "output_file": None,
        }

    _progress(f"Completed {safe_filename}: created {count} chunk(s) -> {output_file}")

    return {
        "message": "Processed successfully",
        "chunks_created": count,
        "output_file": output_file,
        "ocr_used": use_ocr,
        "bart_headers_used": use_bart,
    }