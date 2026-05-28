# app/quiz/quiz_router.py
"""
FastAPI router for the quiz processing pipeline.

Endpoint:
    POST /quiz/process

Request body:
    {
        "file_path": "string",   // local absolute path OR http/https URL
        "file_type": "string"    // pdf | docx | pptx | txt | csv
    }

Response:
    List of quiz chunk objects — one per usable, high-quality chunk.
    Each object contains:
        chunk_index           — sequential index (0-based, post-filtering)
        text                  — clean chunk text
        context_prev_sentence — boundary context from preceding chunk (null if first)
        context_next_sentence — boundary context from following chunk (null if last)
        semantic_score        — cosine similarity coherence score
        quality_score         — composite validator score (only >= 0.50 included)
        bloom_level           — Bloom's taxonomy level
        chunk_type            — definition | process | comparison | example | argument
        concepts              — list of 1-5 core concepts
        keywords              — list of 1-6 specific technical terms

NOT in response:
    - embeddings
    - micro_header / text_with_context
    - page_start / page_end
    - usable / usability_reason / question_targets (internal LLM fields)

The AI service does NOT write to the database.
The backend that calls this endpoint is responsible for DB persistence.
"""

import os
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..router import validate_file, validate_file_type, route_file
from ..file_loader import download_if_url
from .quiz_cleaner import clean_text_for_quiz
from .quiz_chunker import chunk_text_for_quiz
from .quiz_metadata import extract_quiz_metadata

log = logging.getLogger("quiz_router")
router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class QuizFilePayload(BaseModel):
    """
    Request body — matches the style of the existing RAG /extract/embed endpoint.
    file_path may be a local absolute path or an http/https URL.
    """
    file_path: str
    file_type: str


class QuizChunkResponse(BaseModel):
    """
    Response schema for a single quiz chunk.

    All chunks in the list have already been filtered:
      - quality_score >= 0.50
      - semantic_score >= 0.20
      - usable=true (LLM classification)
    """
    chunk_index: int
    text: str
    context_prev_sentence: Optional[str] = None
    context_next_sentence: Optional[str] = None
    semantic_score: float
    quality_score: float
    bloom_level: str
    chunk_type: str
    concepts: List[str]
    keywords: List[str]


# ═══════════════════════════════════════════════════════════════
# ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.post("/process", response_model=List[QuizChunkResponse])
def process_quiz_file(payload: QuizFilePayload):
    """
    Full quiz processing pipeline:

      1. Download file if URL, or use local path directly
      2. Validate file existence and supported type
      3. Extract raw text (PDF / DOCX / PPTX / TXT / CSV)
      4. Quiz-specific cleaning (strips __PGNUM_N__ completely)
      5. Quiz-specific semantic chunking (cosine-similarity boundary detection)
         — embeddings used only internally; NOT stored or returned
      6. Inline Groq LLM metadata extraction (bloom_level, chunk_type,
         concepts, keywords)  with model rotation on rate limits
      7. Filter: drop chunks where usable=false OR quality_score < 0.50
      8. Return clean, enriched chunk list

    The AI service does NOT write anything to the database.
    The backend is responsible for saving the returned chunks to PostgreSQL.
    """
    local_file: Optional[str] = None
    downloaded = False

    try:
        # ── Step 1: Download or resolve local path ─────────────────────────────
        local_file = download_if_url(payload.file_path)
        downloaded = local_file != payload.file_path

        # ── Step 2: Validate ───────────────────────────────────────────────────
        validate_file(local_file)
        validate_file_type(payload.file_type)

        # ── Step 3: Parse raw text ─────────────────────────────────────────────
        log.info("[QuizPipeline] Parsing %s (%s)", payload.file_path, payload.file_type)
        raw_text = route_file(local_file, payload.file_type)

        if not raw_text or not raw_text.strip():
            raise ValueError("Extracted text is empty — check the file content.")

        # ── Step 4: Quiz-specific cleaning ─────────────────────────────────────
        # Strips __PGNUM_N__ markers completely (unlike RAG which preserves them).
        log.info("[QuizPipeline] Cleaning text...")
        cleaned_text = clean_text_for_quiz(raw_text)

        if not cleaned_text.strip():
            raise ValueError("Text is empty after cleaning.")

        # ── Step 5: Quiz-specific semantic chunking ────────────────────────────
        # Cosine-similarity boundary detection via all-MiniLM-L6-v2.
        # Embeddings are used ONLY during this step and are NOT returned.
        # Outputs list of dicts with: chunk_index, text, context_prev_sentence,
        # context_next_sentence, semantic_score, quality_score.
        log.info("[QuizPipeline] Chunking text...")
        chunks = chunk_text_for_quiz(cleaned_text)

        if not chunks:
            log.warning("[QuizPipeline] Chunking produced 0 results for %s", payload.file_path)
            return []

        # ── Step 6: Metadata extraction ────────────────────────────────────────
        # Calls Groq API (with model rotation on rate limits) to extract:
        #   bloom_level, chunk_type, concepts, keywords
        # Drops chunks classified as usable=false.
        log.info("[QuizPipeline] Extracting metadata for %d chunks...", len(chunks))
        enriched_chunks = extract_quiz_metadata(chunks)

        log.info(
            "[QuizPipeline] Done. Returning %d enriched chunks for %s.",
            len(enriched_chunks), payload.file_path,
        )
        return enriched_chunks

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        log.exception("[QuizPipeline] Unexpected error for %s", payload.file_path)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")

    finally:
        # Clean up any temporarily downloaded file
        if downloaded and local_file and os.path.exists(local_file):
            os.remove(local_file)
