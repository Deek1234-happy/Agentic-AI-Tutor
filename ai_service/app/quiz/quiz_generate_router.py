# app/quiz/quiz_generate_router.py
"""
FastAPI router for MCQ generation from pre-processed quiz chunks.

Endpoint:
    POST /quiz/generate

Request body:
    {
        "chunks": [
            {
                "chunk_id":                 "uuid",
                "chunk_text":               "string",
                "bloom_level":              "string",
                "chunk_type":               "string",
                "concepts":                 ["string"],
                "keywords":                 ["string"],
                "context_prev_sentence":    "string | null",
                "context_next_sentence":    "string | null"
            }
        ],
        "mcqs_per_chunk": 3          // optional, 1-4, default 3
    }

Response:
    List of MCQ objects — one per generated question.
    Each object contains:
        question_text    — the question stem
        options          — list of {label, text}  (A/B/C/D, shuffled)
        correct_option   — answer key after shuffle ("A" | "B" | "C" | "D")
        explanation      — 1-2 sentence justification
        concept          — from input metadata, NOT model output
        bloom_level      — from input metadata, NOT model output
        chunk_id         — passthrough from input

Notes:
    - The model is MOCKED for now. Replace quiz_generator._mock_model_call()
      with real inference when the fine-tuned Qwen model is loaded.
    - The AI service does NOT read from or write to the database.
    - The backend is responsible for DB reads (quiz_chunks table) and
      persisting the generated MCQs.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from .quiz_prompt_builder import prepare_all_model_inputs
from .quiz_generator import generate_mcqs

log = logging.getLogger("quiz_generate_router")
router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class QuizChunkInput(BaseModel):
    """
    A single quiz chunk from the backend's content.quiz_chunks table.
    The backend reads from the DB and forwards these fields.
    """
    chunk_id: str
    chunk_text: str
    bloom_level: str = "understand"
    chunk_type: str = "definition"
    concepts: List[str] = []
    keywords: List[str] = []
    context_prev_sentence: Optional[str] = None
    context_next_sentence: Optional[str] = None


class QuizGeneratePayload(BaseModel):
    """
    Request body for POST /quiz/generate.

    chunks:
        List of chunk data objects from the quiz_chunks DB table.
    mcqs_per_chunk:
        How many MCQ slots to generate per chunk (1–4).
        Default 3. Directly controls the slot assignment logic.
    """
    chunks: List[QuizChunkInput]
    mcqs_per_chunk: int = Field(default=3, ge=1, le=4)


class MCQOption(BaseModel):
    """Single option in the MCQ response."""
    label: str       # "A" | "B" | "C" | "D"
    text: str


class MCQResponse(BaseModel):
    """A single generated MCQ in the API response."""
    question_text: str
    options: List[MCQOption]
    correct_option: str       # "A" | "B" | "C" | "D"
    explanation: str
    concept: str              # from input metadata, NOT model output
    bloom_level: str          # from input metadata, NOT model output
    chunk_id: str


# ═══════════════════════════════════════════════════════════════
# ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.post("/generate", response_model=List[MCQResponse])
def generate_quiz(payload: QuizGeneratePayload):
    """
    Generate MCQs from pre-processed quiz chunks.

    Pipeline:
      1. Validate input (Pydantic handles this)
      2. Build model-ready prompts  (quiz_prompt_builder)
         - clean_concepts()  → validate / NLP fallback
         - assign_slots()    → 2-4 MCQ slots per chunk
         - build_model_input() → exact SFT-format prompt per slot
      3. Run model inference  (quiz_generator — MOCKED for now)
         - Call model per slot
         - Parse JSON output
         - Pydantic validation
         - Option shuffling
      4. Return formatted MCQ list

    The model is MOCKED — replace quiz_generator._mock_model_call()
    with real Qwen inference when the fine-tuned model is loaded.
    """
    if not payload.chunks:
        raise HTTPException(status_code=400, detail="No chunks provided.")

    try:
        # Convert Pydantic models to dicts for the prompt builder
        chunks_data = [chunk.model_dump() for chunk in payload.chunks]

        log.info(
            "[QuizGenerate] Processing %d chunks, mcqs_per_chunk=%d",
            len(chunks_data),
            payload.mcqs_per_chunk,
        )

        # Step 1: Build model-ready prompts
        model_inputs = prepare_all_model_inputs(
            chunks=chunks_data,
            mcqs_per_chunk=payload.mcqs_per_chunk,
        )

        log.info(
            "[QuizGenerate] Built %d model inputs from %d chunks",
            len(model_inputs),
            len(chunks_data),
        )

        if not model_inputs:
            log.warning("[QuizGenerate] No model inputs generated. Returning empty list.")
            return []

        # Step 2: Generate MCQs (mocked model inference)
        mcq_results = generate_mcqs(model_inputs)

        log.info(
            "[QuizGenerate] Done. Returning %d MCQs for %d chunks.",
            len(mcq_results),
            len(chunks_data),
        )

        return mcq_results

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        log.exception("[QuizGenerate] Unexpected error")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")
