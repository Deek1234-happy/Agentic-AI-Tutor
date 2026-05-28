# app/quiz/quiz_metadata.py
"""
Quiz metadata extractor — Groq LLM integration.

Calls the Groq API (llama-3.1-8b-instant by default) to extract structured
metadata for each quiz chunk.  Metadata is merged directly into the chunk
dicts in-place and returned — no files are written.

Model rotation strategy (Q3 decision):
  When a model hits a rate-limit (HTTP 429) the extractor rotates to the
  next model in the priority list and retries the same batch immediately.
  Only after ALL models have been exhausted does it apply exponential
  backoff and retry from the top of the list.

  Priority order (configured in QuizMetadataConfig):
    1. llama-3.1-8b-instant   — fastest, highest free RPD
    2. llama-3.3-70b-versatile — slower but larger capacity
    3. gemma2-9b-it            — Google model, separate rate-limit bucket
    4. mixtral-8x7b-32768      — Mistral, separate bucket

Fields extracted per chunk:
  bloom_level  — Bloom's taxonomy level (remember/understand/apply/analyze/evaluate/create)
  chunk_type   — definition | process | comparison | example | argument
  concepts     — list of 1–5 core ideas (1–4 words each)
  keywords     — list of 1–6 specific technical terms from the chunk text

Fields intentionally NOT extracted / NOT in response:
  usable           — internal LLM filter field; unusable chunks are dropped here
  usability_reason — internal LLM field; not needed by backend
  question_targets — removed per design decision Q2

Public API:
    from .quiz_metadata import extract_quiz_metadata
    enriched_chunks = extract_quiz_metadata(chunks)
"""

import os
import re
import json
import time
import logging
from typing import Dict, List, Optional

from groq import Groq

from .quiz_config import QuizMetadataConfig

log = logging.getLogger("quiz_metadata")


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

_USABILITY_CRITERIA = """
A chunk is USABLE for MCQ generation if it contains at least ONE of:
  1. A definition, explanation, or description of a concept, algorithm, or technique
  2. A comparison between two or more methods, approaches, or concepts
  3. A cause-and-effect or mechanism relationship (why/how something works)
  4. An application scenario or use-case description
  5. A step-by-step process or algorithm description
  6. Properties, characteristics, or trade-offs of a method
  7. A mathematical concept explained in words (not just bare symbols)

A chunk is NOT USABLE (mark usable=false) ONLY IF it matches one or more of:
  - Pure OCR noise with no recoverable educational content
  - Only a list of symbols, formulas, or variable names without any explanation
  - Only a bibliography, references section, or citation list
  - Only figure/table captions with no explanatory prose
  - Fewer than 3 complete sentences of educational content after removing noise

When in doubt, mark usable=true.
""".strip()

_SYSTEM_PROMPT = f"""You are an expert AI educator preparing metadata for automatic MCQ generation.

You will receive up to four chunks of text from AI educational materials.
For each chunk, extract structured metadata following the rules below exactly.

USABILITY CRITERIA:
{_USABILITY_CRITERIA}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOOM'S TAXONOMY — pick the MOST ACCURATE level, not the highest possible
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  remember   — chunk defines a term or states a fact
  understand — chunk explains why/how, describes a mechanism or interpretation
  apply      — chunk shows or describes how to USE a method in a concrete scenario
  analyze    — chunk compares multiple methods, breaks down relationships, or identifies root causes
  evaluate   — chunk judges trade-offs, recommends one approach, or critiques a method
  create     — chunk proposes designing, building, or constructing something new

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHUNK TYPES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  definition  — defines or introduces a concept
  process     — describes steps, algorithms, or procedures
  comparison  — contrasts two or more methods or concepts
  example     — illustrates with a concrete case or application
  argument    — presents reasoning, evidence, or justification for a claim

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPTS — the core ideas of THIS specific chunk
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rules:
  - Each concept: 1–4 words, no more.
  - Concepts must be CENTRAL to this specific chunk.
  - Extract the SPECIFIC idea discussed, not a generic category name.
  - Maximum 5 concepts.

  BAD concepts (too generic): "convergence", "performance", "machine learning"
  GOOD concepts (specific):   "lookahead gradient", "exponential moving average",
                               "neuron co-adaptation", "adaptive learning rate decay"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEYWORDS — specific technical terms from the chunk text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rules:
  - Keywords must appear LITERALLY in the chunk text (exact or near-exact match).
  - Must NOT duplicate anything in the concepts list.
  - Do NOT include: code variable names, garbled OCR, vague terms ("algorithm", "method").
  - Maximum 6 keywords.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON array, one object per chunk, in input order.
No markdown, no explanation, no text before or after the JSON array.
Each object must have exactly these keys:
  chunk_id, usable, usability_reason, bloom_level, chunk_type, concepts, keywords

If usable is false, still fill the other fields as best you can.
"""


def _build_user_prompt(batch: List[Dict], cfg: QuizMetadataConfig) -> str:
    """Build the user-turn prompt for a batch of 1–2 chunks."""
    parts = []
    for i, chunk in enumerate(batch, start=1):
        prev = chunk.get("context_prev_sentence")
        nxt  = chunk.get("context_next_sentence")

        context_block = ""
        if prev:
            context_block += f"[Previous context]: {prev}\n"
        if nxt:
            context_block += f"[Following context]: {nxt}\n"
        if context_block:
            context_block += "\n"

        text = chunk.get("text", "")
        words = text.split()
        if len(words) > cfg.max_chunk_words:
            text = " ".join(words[:cfg.max_chunk_words]) + " [truncated]"

        parts.append(
            f"--- CHUNK {i} (id: {chunk['_temp_id']}) ---\n"
            f"{context_block}"
            f"{text}\n"
        )

    joined = "\n".join(parts)
    return (
        f"Extract metadata for the following {len(batch)} chunk(s).\n\n"
        f"{joined}\n"
        f"Return a JSON array with {len(batch)} object(s), one per chunk, in order."
    )


# ═══════════════════════════════════════════════════════════════
# RESPONSE PARSING + VALIDATION
# ═══════════════════════════════════════════════════════════════

_VALID_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
_VALID_TYPES = {"definition", "process", "comparison", "example", "argument"}


def _parse_groq_response(raw: str, batch: List[Dict]) -> Optional[List[Dict]]:
    """Parse raw LLM response into a list of validated metadata dicts."""
    raw = re.sub(r"```json\s*|```\s*", "", raw).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        array_match  = re.search(r"\[.*\]", raw, re.DOTALL)
        object_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if array_match:
            try:
                parsed = json.loads(array_match.group(0))
            except Exception:
                log.error("Could not parse JSON array from response: %s", raw[:200])
                return None
        elif object_match:
            try:
                parsed = json.loads(object_match.group(0))
            except Exception:
                log.error("Could not parse JSON object from response: %s", raw[:200])
                return None
        else:
            log.error("No JSON found in response: %s", raw[:200])
            return None

    # Normalise to list
    if isinstance(parsed, dict):
        if "results" in parsed:
            parsed = parsed["results"]
        elif all(str(i) in parsed for i in range(len(batch))):
            parsed = [parsed[str(i)] for i in range(len(batch))]
        else:
            parsed = [parsed]

    if not isinstance(parsed, list):
        log.error("Unexpected parsed type %s", type(parsed))
        return None

    # Pad / trim to batch size
    while len(parsed) < len(batch):
        parsed.append(None)
    parsed = parsed[:len(batch)]

    return [_validate_metadata(item, chunk) for item, chunk in zip(parsed, batch)]


def _validate_metadata(item: Optional[dict], chunk: dict) -> dict:
    """Ensure all required fields are present with valid values."""
    if not isinstance(item, dict):
        item = {}

    item["chunk_id"] = chunk["_temp_id"]

    # usable (internal — used to filter; NOT in final response)
    if not isinstance(item.get("usable"), bool):
        item["usable"] = True

    # usability_reason (internal — NOT in final response)
    if not isinstance(item.get("usability_reason"), str):
        item["usability_reason"] = ""

    # bloom_level
    if item.get("bloom_level") not in _VALID_BLOOM:
        item["bloom_level"] = "understand"

    # chunk_type
    if item.get("chunk_type") not in _VALID_TYPES:
        item["chunk_type"] = "definition"

    # concepts
    if not isinstance(item.get("concepts"), list) or not item["concepts"]:
        item["concepts"] = ["general concept"]
    else:
        normalised, seen = [], set()
        for c in item["concepts"]:
            if isinstance(c, str):
                normed = c.strip().lower()
                if normed and normed not in seen:
                    seen.add(normed)
                    normalised.append(normed)
        item["concepts"] = (normalised if normalised else ["general concept"])[:5]

    # keywords
    if not isinstance(item.get("keywords"), list) or not item["keywords"]:
        item["keywords"] = ["general"]
    else:
        item["keywords"] = [
            k.strip() for k in item["keywords"]
            if isinstance(k, str) and k.strip()
        ]
        if not item["keywords"]:
            item["keywords"] = ["general"]
    item["keywords"] = item["keywords"][:6]

    return item


def _fallback_metadata(temp_id: str) -> dict:
    """Safe defaults used when all API calls fail after all retries + rotations."""
    return {
        "chunk_id":         temp_id,
        "usable":           True,
        "usability_reason": "",
        "bloom_level":      "understand",
        "chunk_type":       "definition",
        "concepts":         ["general concept"],
        "keywords":         ["general"],
    }


# ═══════════════════════════════════════════════════════════════
# GROQ CALL WITH MODEL ROTATION
# ═══════════════════════════════════════════════════════════════

def _call_groq_with_rotation(
    client: Groq,
    batch: List[Dict],
    cfg: QuizMetadataConfig,
    system_prompt: str,
) -> Optional[List[Dict]]:
    """
    Call Groq API for a batch.  On rate-limit (429) rotate to the next model
    in cfg.models immediately.  Only after all models are exhausted does
    exponential backoff kick in before retrying from the top.

    Returns a list of validated metadata dicts, or None on complete failure.
    """
    models = list(cfg.models)
    n_models = len(models)
    user_prompt = _build_user_prompt(batch, cfg)

    global_attempt = 0
    model_idx = 0

    while global_attempt < cfg.max_retries * n_models:
        model = models[model_idx % n_models]
        global_attempt += 1

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=800,   # 800 handles up to 4 JSON objects (~200 tokens each)
                # json_object mode only works reliably for single objects;
                # use free-form for batches and let _parse_groq_response handle it.
                **({"response_format": {"type": "json_object"}} if len(batch) == 1 else {}),
            )
            raw = response.choices[0].message.content.strip()
            result = _parse_groq_response(raw, batch)
            if result is not None:
                if model != models[0]:
                    log.info("[QuizMeta] Success on model=%s", model)
                return result

        except Exception as exc:
            err = str(exc)
            is_rate_limit = "429" in err or "rate_limit" in err.lower() or "rate limit" in err.lower()

            if is_rate_limit:
                # Try to parse Retry-After from the error message
                retry_after_match = re.search(
                    r"retry.after[^\d]*(\d+(?:\.\d+)?)", err, re.IGNORECASE
                )
                retry_after = float(retry_after_match.group(1)) + 0.5 if retry_after_match else 0

                next_model = models[(model_idx + 1) % n_models]
                log.warning(
                    "[QuizMeta] Rate limit on model=%s (attempt %d). "
                    "Rotating to model=%s.",
                    model, global_attempt, next_model,
                )
                model_idx += 1  # rotate immediately — no sleep before trying next model

                # If we've cycled through all models, apply backoff before restarting
                if model_idx % n_models == 0:
                    cycle = model_idx // n_models
                    backoff = max(retry_after, cfg.base_backoff ** cycle)
                    log.warning(
                        "[QuizMeta] All models exhausted (cycle %d). "
                        "Backing off %.1fs before retrying from top.",
                        cycle, backoff,
                    )
                    time.sleep(backoff)
                    model_idx = 0  # restart from preferred model

            else:
                # Non-rate-limit error — retry same model with linear backoff
                log.error("[QuizMeta] API error (model=%s, attempt %d): %s", model, global_attempt, exc)
                time.sleep(cfg.base_backoff * (global_attempt % cfg.max_retries + 1))

    log.error("[QuizMeta] All retries exhausted for batch. Using fallback metadata.")
    return None


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def extract_quiz_metadata(chunks: List[Dict]) -> List[Dict]:
    """
    Enrich quiz chunk dicts with LLM-extracted metadata.

    For each chunk the following fields are added in-place:
      bloom_level, chunk_type, concepts, keywords

    Chunks classified by the LLM as usable=false are DROPPED from the
    returned list (per Q1 decision — filter on AI service side).

    Fields NOT included in output (internal LLM fields):
      usable, usability_reason

    Args:
        chunks: List of dicts from chunk_text_for_quiz(), each with at minimum:
                  chunk_index, text, context_prev_sentence, context_next_sentence,
                  semantic_score, quality_score

    Returns:
        Filtered, enriched list of chunk dicts (chunk_index re-numbered after filtering).
    """
    if not chunks:
        return []

    cfg = QuizMetadataConfig()
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        log.error("[QuizMeta] GROQ_API_KEY not set. Returning chunks with fallback metadata.")
        return _apply_fallback_metadata(chunks)

    # Explicitly set base_url to the Groq root URL.
    # The .env may contain GROQ_BASE_URL=https://api.groq.com/openai/v1 which
    # the Groq SDK reads automatically and then APPENDS /openai/v1 again,
    # producing the broken path /openai/v1/openai/v1/chat/completions.
    # Passing base_url here overrides the env variable entirely.
    client = Groq(api_key=api_key, base_url="https://api.groq.com")

    # Assign temporary IDs for tracking across batches
    for i, chunk in enumerate(chunks):
        chunk["_temp_id"] = f"quiz_chunk_{i}"

    enriched: List[Dict] = []
    total = len(chunks)

    print(f"[QuizMeta] Extracting metadata for {total} chunks...", flush=True)

    for batch_start in range(0, total, cfg.batch_size):
        batch = chunks[batch_start: batch_start + cfg.batch_size]

        metadata_list = _call_groq_with_rotation(client, batch, cfg, _SYSTEM_PROMPT)

        if metadata_list is None:
            # Total failure — use fallback (marks as usable=True to not lose data)
            log.warning("[QuizMeta] Batch %d failed completely. Using fallback.", batch_start)
            for chunk in batch:
                meta = _fallback_metadata(chunk["_temp_id"])
                enriched.append(_merge_metadata(chunk, meta))
            continue

        for chunk, meta in zip(batch, metadata_list):
            # Drop chunks the LLM classified as not usable for MCQ generation
            if not meta.get("usable", True):
                log.info(
                    "[QuizMeta] Dropping chunk %s (usable=false): %s",
                    chunk["_temp_id"],
                    meta.get("usability_reason", ""),
                )
                continue
            enriched.append(_merge_metadata(chunk, meta))

        # Respect TPM limits between batches
        if batch_start + cfg.batch_size < total:
            time.sleep(cfg.inter_batch_sleep)

    # Re-number chunk_index after filtering
    for idx, chunk in enumerate(enriched):
        chunk["chunk_index"] = idx

    print(
        f"[QuizMeta] Done. {len(enriched)}/{total} chunks kept after usability filter.",
        flush=True,
    )
    return enriched


def _merge_metadata(chunk: Dict, meta: Dict) -> Dict:
    """
    Merge LLM metadata into chunk dict.

    Only the fields needed for the API response are kept.
    Internal fields (usable, usability_reason, _temp_id) are stripped.
    """
    return {
        "chunk_index":           chunk.get("chunk_index", 0),
        "text":                  chunk.get("text", ""),
        "context_prev_sentence": chunk.get("context_prev_sentence"),
        "context_next_sentence": chunk.get("context_next_sentence"),
        "semantic_score":        chunk.get("semantic_score", 0.0),
        "quality_score":         chunk.get("quality_score", 0.0),
        # LLM-extracted fields
        "bloom_level":           meta.get("bloom_level", "understand"),
        "chunk_type":            meta.get("chunk_type", "definition"),
        "concepts":              meta.get("concepts", ["general concept"]),
        "keywords":              meta.get("keywords", ["general"]),
    }


def _apply_fallback_metadata(chunks: List[Dict]) -> List[Dict]:
    """Attach fallback metadata to all chunks when Groq is unavailable."""
    result = []
    for chunk in chunks:
        result.append({
            "chunk_index":           chunk.get("chunk_index", 0),
            "text":                  chunk.get("text", ""),
            "context_prev_sentence": chunk.get("context_prev_sentence"),
            "context_next_sentence": chunk.get("context_next_sentence"),
            "semantic_score":        chunk.get("semantic_score", 0.0),
            "quality_score":         chunk.get("quality_score", 0.0),
            "bloom_level":           "understand",
            "chunk_type":            "definition",
            "concepts":              ["general concept"],
            "keywords":              ["general"],
        })
    return result
