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
        "number_of_questions": 10,       // required, 1-50
        "mcqs_per_chunk": 4              // optional, 1-4, default 4
    }

Response:
    {
        "mcqs": [ ... list of MCQ objects ... ],
        "requested_count": 10,
        "available_slots": 21,
        "generated_count": 10
    }

Notes:
    - number_of_questions controls how many MCQs the final quiz contains.
    - mcqs_per_chunk controls how many slots are generated PER CHUNK
      (default 4 = maximum). More slots = larger pool for smart selection.
    - The slot selector picks the best N slots to maximise diversity
      across chunks, Bloom levels, and concepts.
    - The AI service does NOT read from or write to the database.
    - The backend is responsible for DB reads (quiz_chunks table) and
      persisting the generated MCQs.
"""

import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from .quiz_prompt_builder import prepare_all_model_inputs
from .quiz_slot_selector import select_slots
from .quiz_generator import generate_mcqs

log = logging.getLogger("quiz_generate_router")
router = APIRouter()

# Log directory — ai_service/logs/
_LOG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "logs")
)


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
    number_of_questions:
        Total number of MCQs the user wants in the quiz (1–50).
        The slot selector will pick the best N slots to maximise
        diversity across chunks, Bloom levels, and concepts.
        If number_of_questions > available slots, all slots are used.
    mcqs_per_chunk:
        How many slots to generate per chunk (1–4). Default 4 (maximum).
        Higher values give the selector a larger pool to choose from.
        Optional — if not sent, defaults to 4.
    """
    chunks: List[QuizChunkInput]
    number_of_questions: int = Field(..., ge=1, le=50)
    mcqs_per_chunk: int = Field(default=4, ge=1, le=4)


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
    document_id: str = ""     # from input metadata, NOT model output


class QuizGenerateResponse(BaseModel):
    """
    Wrapped response for POST /quiz/generate.

    Includes the generated MCQs plus metadata about the selection process
    so the client knows if the requested count was capped.
    """
    mcqs: List[MCQResponse]
    requested_count: int      # what the user asked for
    available_slots: int      # total slots the pipeline produced
    generated_count: int      # actual MCQs returned (after inference + dedup)


# ═══════════════════════════════════════════════════════════════
# ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.post("/generate", response_model=QuizGenerateResponse)
def generate_quiz(payload: QuizGeneratePayload):
    """
    Generate MCQs from pre-processed quiz chunks.

    Pipeline:
      1. Validate input (Pydantic handles this)
      2. Build model-ready prompts  (quiz_prompt_builder)
      3. Smart slot selection  (quiz_slot_selector)
      4. Run model inference  (quiz_generator)
      5. Write trace log to ai_service/logs/
      6. Return wrapped response with metadata
    """
    if not payload.chunks:
        raise HTTPException(status_code=400, detail="No chunks provided.")

    run_start = time.time()
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # ── Trace log dict — built up through the pipeline ────────
    trace: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": {
            "number_of_questions": payload.number_of_questions,
            "mcqs_per_chunk": payload.mcqs_per_chunk,
            "num_chunks": len(payload.chunks),
            "chunks_summary": [],
        },
        "slot_generation": {},
        "slot_selection": {},
        "inference": {},
        "response": {},
        "error": None,
    }

    # Summarise input chunks (no full text — keep log concise)
    for chunk in payload.chunks:
        trace["request"]["chunks_summary"].append({
            "chunk_id": chunk.chunk_id,
            "bloom_level": chunk.bloom_level,
            "chunk_type": chunk.chunk_type,
            "concepts": chunk.concepts,
            "keywords": chunk.keywords,
            "text_length": len(chunk.chunk_text),
        })

    try:
        chunks_data = [chunk.model_dump() for chunk in payload.chunks]

        log.info(
            "[QuizGenerate] Processing %d chunks, number_of_questions=%d, mcqs_per_chunk=%d",
            len(chunks_data),
            payload.number_of_questions,
            payload.mcqs_per_chunk,
        )

        # ── Step 1: Build full pool of model-ready prompts ────
        all_model_inputs = prepare_all_model_inputs(
            chunks=chunks_data,
            mcqs_per_chunk=payload.mcqs_per_chunk,
        )

        total_available = len(all_model_inputs)

        # Log all generated slots
        trace["slot_generation"] = {
            "total_slots": total_available,
            "slots": [
                {
                    "index": i,
                    "chunk_id": inp.get("slot_metadata", {}).get("chunk_id", ""),
                    "concept": inp.get("slot_metadata", {}).get("concept", ""),
                    "bloom_level": inp.get("slot_metadata", {}).get("bloom_level", ""),
                    "slot_type": inp.get("slot_metadata", {}).get("slot_type", ""),
                }
                for i, inp in enumerate(all_model_inputs)
            ],
        }

        log.info(
            "[QuizGenerate] Built %d model inputs (slots) from %d chunks",
            total_available,
            len(chunks_data),
        )

        if not all_model_inputs:
            log.warning("[QuizGenerate] No model inputs generated. Returning empty response.")
            trace["response"] = {"generated_count": 0, "reason": "no_slots_generated"}
            _write_trace(trace, run_timestamp)
            return QuizGenerateResponse(
                mcqs=[],
                requested_count=payload.number_of_questions,
                available_slots=0,
                generated_count=0,
            )

        # ── Step 2: Smart slot selection ──────────────────────
        selected_inputs = select_slots(
            model_inputs=all_model_inputs,
            requested_count=payload.number_of_questions,
        )

        # Build selection trace
        selected_chunk_dist = Counter()
        selected_bloom_dist = Counter()
        selected_details = []
        for inp in selected_inputs:
            meta = inp.get("slot_metadata", {})
            cid = meta.get("chunk_id", "")
            bloom = meta.get("bloom_level", "")
            selected_chunk_dist[cid] += 1
            selected_bloom_dist[bloom] += 1
            selected_details.append({
                "chunk_id": cid,
                "concept": meta.get("concept", ""),
                "bloom_level": bloom,
                "slot_type": meta.get("slot_type", ""),
            })

        trace["slot_selection"] = {
            "requested": payload.number_of_questions,
            "available": total_available,
            "selected": len(selected_inputs),
            "capped": payload.number_of_questions > total_available,
            "chunk_distribution": dict(selected_chunk_dist),
            "bloom_distribution": dict(selected_bloom_dist),
            "selected_slots": selected_details,
        }

        log.info(
            "[QuizGenerate] Selected %d slots from %d available",
            len(selected_inputs),
            total_available,
        )

        # ── Step 3: Generate MCQs ─────────────────────────────
        mcq_results = generate_mcqs(selected_inputs)

        elapsed = time.time() - run_start

        # Build inference trace
        trace["inference"] = {
            "slots_sent": len(selected_inputs),
            "mcqs_returned": len(mcq_results),
            "elapsed_seconds": round(elapsed, 2),
            "mcqs": [
                {
                    "question_text": mcq.get("question_text", "")[:100] + "...",
                    "concept": mcq.get("concept", ""),
                    "bloom_level": mcq.get("bloom_level", ""),
                    "chunk_id": mcq.get("chunk_id", ""),
                    "correct_option": mcq.get("correct_option", ""),
                }
                for mcq in mcq_results
            ],
        }

        trace["response"] = {
            "requested_count": payload.number_of_questions,
            "available_slots": total_available,
            "generated_count": len(mcq_results),
            "total_elapsed_seconds": round(elapsed, 2),
        }

        log.info(
            "[QuizGenerate] Done. Generated %d MCQs in %.1fs (requested=%d, available=%d).",
            len(mcq_results),
            elapsed,
            payload.number_of_questions,
            total_available,
        )

        # ── Write trace log ───────────────────────────────────
        _write_trace(trace, run_timestamp)

        return QuizGenerateResponse(
            mcqs=mcq_results,
            requested_count=payload.number_of_questions,
            available_slots=total_available,
            generated_count=len(mcq_results),
        )

    except ValueError as exc:
        trace["error"] = {"type": "ValueError", "message": str(exc)}
        _write_trace(trace, run_timestamp)
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        trace["error"] = {"type": type(exc).__name__, "message": str(exc)}
        _write_trace(trace, run_timestamp)
        log.exception("[QuizGenerate] Unexpected error")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")


def _write_trace(trace: dict, run_timestamp: str) -> None:
    """
    Write the pipeline trace to a timestamped JSON file.

    File: ai_service/logs/quiz_trace_YYYYMMDD_HHMMSS.json
    """
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        log_file = os.path.join(_LOG_DIR, f"quiz_trace_{run_timestamp}.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(trace, f, indent=2, ensure_ascii=False)
        log.info("[QuizGenerate] Trace log written to %s", log_file)
    except Exception as e:
        log.error("[QuizGenerate] Failed to write trace log: %s", e)

