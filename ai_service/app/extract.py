from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union

from .router import validate_file, validate_file_type, route_file
from .text_cleaner import clean_text
from .chunker import chunk_text

router = APIRouter()


# ============================================================
# Request / Response Models
# ============================================================

class FilePayload(BaseModel):
    file_id: str
    file_path: str
    file_type: str


class ChunkResponse(BaseModel):
    file_id: str
    chunk_id: str
    source_type: str
    page_or_slide: Optional[Union[str, List[str]]]
    section: Optional[Union[str, List[str]]]
    text: str


# ============================================================
# Extraction + Chunking Endpoint
# ============================================================

@router.post("/", response_model=List[ChunkResponse])
def extract_and_chunk_file(payload: FilePayload):
    """
    1. Validate file
    2. Extract raw text (PDF/DOCX/PPTX/TXT/CSV)
    3. Clean text
    4. Apply dynamic chunking
    5. Return embedding-ready chunks
    """
    try:
        # --------------------
        # Validation
        # --------------------
        validate_file(payload.file_path)
        validate_file_type(payload.file_type)

        # --------------------
        # Extraction
        # --------------------
        raw_text = route_file(
            payload.file_path,
            payload.file_type
        )

        if not raw_text.strip():
            raise ValueError("Extracted text is empty")

        # --------------------
        # Cleaning
        # --------------------
        cleaned_text = clean_text(raw_text)

        # --------------------
        # Dynamic chunking
        # --------------------
        chunks = chunk_text(
            text=cleaned_text,
            file_id=payload.file_id,
            source_type=payload.file_type
        )

        return chunks

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
