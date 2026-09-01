# app/extract.py
import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union

from .router import validate_file, validate_file_type, route_file
from .text_cleaner import clean_text
from .chunker import chunk_text
from .embedding import embed_texts
from .file_loader import download_if_url

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Request / Response Models  (unchanged from original)
# ============================================================

class FilePayload(BaseModel):
    # file_id: str
    file_path: str
    file_type: str


class ChunkResponse(BaseModel):
    file_id: str
    chunk_id: str
    source_type: str
    page_start: int | None
    page_end: int | None
    text: str


# ============================================================
# Extraction + Chunking Endpoint
# ============================================================

@router.post("/", response_model=List[ChunkResponse])
def extract_and_chunk_file(payload: FilePayload):
    """
    1. Validate file
    2. Extract raw text (PDF/DOCX/PPTX/TXT/CSV)
    3. Clean text  (advanced TextCleaner — quiz-quality)
    4. Apply semantic chunking  (SemanticChunker — quiz-quality)
    5. Return embedding-ready chunks
    """
    local_file = None
    downloaded = False

    logger.info("[extract] Received request: file_path=%s file_type=%s", payload.file_path, payload.file_type)

    try:
        logger.info("[extract] Downloading/validating file path: %s", payload.file_path)
        local_file = download_if_url(payload.file_path)
        downloaded = local_file != payload.file_path
        logger.info("[extract] Resolved local file: %s (downloaded=%s)", local_file, downloaded)

        validate_file(local_file)
        logger.info("[extract] File validated: %s", local_file)

        validate_file_type(payload.file_type)
        logger.info("[extract] File type validated: %s", payload.file_type)

        raw_text = route_file(local_file, payload.file_type)
        logger.info("[extract] Raw text extracted. Length=%s", len(raw_text) if raw_text else 0)

        if not raw_text.strip():
            raise ValueError("Extracted text is empty")

        cleaned_text = clean_text(raw_text)
        logger.info("[extract] Text cleaned. Length=%s", len(cleaned_text) if cleaned_text else 0)

        chunks = chunk_text(
            text=cleaned_text,
            source_type=payload.file_type,
        )
        logger.info("[extract] Chunking produced %s chunks", len(chunks))

        # Derive a stable file_id from the filename and stamp each chunk
        file_id = (
            os.path.basename(payload.file_path)
            .rsplit(".", 1)[0]
            .lower()
            .replace(" ", "_")
        )
        for idx, chunk in enumerate(chunks, start=1):
            chunk["file_id"]  = file_id
            chunk["chunk_id"] = f"{file_id}_chunk_{idx}"

        return chunks

    except FileNotFoundError as e:
        logger.exception("[extract] File not found while processing request: file_path=%s file_type=%s", payload.file_path, payload.file_type)
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        logger.exception("[extract] Validation/value error: file_path=%s file_type=%s", payload.file_path, payload.file_type)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception("[extract] Unhandled exception in extraction pipeline: file_path=%s file_type=%s", payload.file_path, payload.file_type)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    finally:
        if downloaded and local_file and os.path.exists(local_file):
            logger.info("[extract] Cleaning up downloaded temp file: %s", local_file)
            os.remove(local_file)


# ============================================================
# Embedding Endpoint
# ============================================================

class EmbeddedChunkResponse(BaseModel):
    # file_id: str
    # chunk_id: str
    # source_type: str
    page_start: int | None
    page_end: int | None
    text: str
    embedding: List[float]


@router.post("/embed", response_model=List[EmbeddedChunkResponse])
def extract_chunk_and_embed(payload: FilePayload):

    local_file = None
    downloaded = False

    logger.info("[embed] Received request: file_path=%s file_type=%s", payload.file_path, payload.file_type)

    try:
        logger.info("[embed] Downloading/validating file path: %s", payload.file_path)
        local_file = download_if_url(payload.file_path)
        downloaded = local_file != payload.file_path
        logger.info("[embed] Resolved local file: %s (downloaded=%s)", local_file, downloaded)

        validate_file(local_file)
        logger.info("[embed] File validated: %s", local_file)

        validate_file_type(payload.file_type)
        logger.info("[embed] File type validated: %s", payload.file_type)

        raw_text = route_file(local_file, payload.file_type)
        logger.info("[embed] Raw text extracted. Length=%s", len(raw_text) if raw_text else 0)

        cleaned_text = clean_text(raw_text)
        logger.info("[embed] Text cleaned. Length=%s", len(cleaned_text) if cleaned_text else 0)

        chunks = chunk_text(
            text=cleaned_text,
            source_type=payload.file_type,
        )
        logger.info("[embed] Chunking produced %s chunks", len(chunks))

        texts = [chunk["text"] for chunk in chunks]
        logger.info("[embed] Embedding %s chunk texts", len(texts))
        embeddings = embed_texts(texts)
        logger.info("[embed] Embedding generation returned %s vectors", len(embeddings))

        for chunk, vector in zip(chunks, embeddings):
            chunk["embedding"] = vector

        return chunks

    except Exception as e:
        logger.exception("[embed] Unhandled exception in embed pipeline: file_path=%s file_type=%s", payload.file_path, payload.file_type)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if downloaded and local_file and os.path.exists(local_file):
            logger.info("[embed] Cleaning up downloaded temp file: %s", local_file)
            os.remove(local_file)