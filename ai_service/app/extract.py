# app/extract.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union

from .router import validate_file, validate_file_type, route_file
from .text_cleaner import clean_text
from .chunker import chunk_text
from .embedding import embed_texts
from .file_loader import download_if_url
import os

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

    try:
        local_file = download_if_url(payload.file_path)
        downloaded = local_file != payload.file_path

        validate_file(local_file)
        validate_file_type(payload.file_type)

        raw_text = route_file(local_file, payload.file_type)

        if not raw_text.strip():
            raise ValueError("Extracted text is empty")

        cleaned_text = clean_text(raw_text)

        chunks = chunk_text(
            text=cleaned_text,
            source_type=payload.file_type,
        )

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
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    finally:
        if downloaded and local_file and os.path.exists(local_file):
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

    try:
        local_file = download_if_url(payload.file_path)
        downloaded = local_file != payload.file_path

        validate_file(local_file)
        validate_file_type(payload.file_type)

        raw_text = route_file(local_file, payload.file_type)

        cleaned_text = clean_text(raw_text)

        chunks = chunk_text(
            text=cleaned_text,
            source_type=payload.file_type,
        )

        texts = [chunk["text"] for chunk in chunks]
        embeddings = embed_texts(texts)

        for chunk, vector in zip(chunks, embeddings):
            chunk["embedding"] = vector

        return chunks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if downloaded and local_file and os.path.exists(local_file):
            os.remove(local_file)