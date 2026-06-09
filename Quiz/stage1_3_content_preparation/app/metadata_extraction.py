"""
S3 — Metadata Extraction
========================
Reads chunks from JSONL files in Quiz/data/global_chunks, calls Groq
(llama-3.1-8b-instant) to extract structured metadata per chunk,
classifies each chunk as usable or not for MCQ generation, and saves
enriched chunks into separate usable / not_usable output folders.

Usage:
    python metadata_extraction.py \
        --output data/metadata/

    # Or specify a custom input folder:
    python metadata_extraction.py \
        --input  data/global_chunks/ \
        --output data/metadata/

    Output structure:
        <output>/usable/       — chunks marked usable=true
        <output>/not_usable/   — chunks marked usable=false

Design decisions:
    - Model  : llama-3.1-8b-instant
    - Batch  : 2 chunks per API call — 30% token savings vs 1-per-call
               with minimal risk of concept conflation between chunks
    - Limit  : TPD=500K tokens/day → ~1,086 chunks/day → 5K in ~4.6 days
    - Cache  : already-processed chunk_ids are skipped on re-run
    - Retry  : exponential backoff on 429, up to 5 attempts per batch
"""

import os
import json
import time
import logging
import argparse
import re
from pathlib import Path
from typing import Optional

from groq import Groq


def load_dotenv_file(dotenv_path: Path) -> None:
    """
    Load environment variables from a .env file into os.environ.
    Existing environment variables are not overwritten.
    """
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("s3_metadata")

# ── config ────────────────────────────────────────────────────────────────────
MODEL          = "llama-3.1-8b-instant"   # 14,400 RPD · 500K TPD · 6K TPM
BATCH_SIZE     = 2                         # chunks per API call
MAX_RETRIES    = 5
BASE_BACKOFF   = 2.0                       # seconds, doubles on each retry
MAX_CHUNK_WORDS = 300                      # truncation guard before sending

# ── chunk usability criteria ─────────────────────────────────────────────────
# These are embedded verbatim in the prompt so the LLM uses them exactly.
USABILITY_CRITERIA = """
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


When in doubt, mark usable=true. Only mark false when the chunk is clearly
unusable by ALL of the usability criteria above.
""".strip()

# ── system prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are an expert AI educator preparing metadata for automatic MCQ generation.

You will receive one or two chunks of text from AI educational materials (textbooks or lecture slides).
For each chunk, extract structured metadata and assess usability for MCQ generation following the rules below exactly.

USABILITY CRITERIA:
{USABILITY_CRITERIA}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOOM'S TAXONOMY — pick the MOST ACCURATE level, not the highest possible
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  remember   — chunk defines a term or states a fact (definitions, names, what is X)
  understand — chunk explains why/how, describes a mechanism or interpretation
  apply      — chunk shows or describes how to USE a method in code or a concrete scenario
  analyze    — chunk compares multiple methods, breaks down relationships, or identifies root causes
  evaluate   — chunk judges trade-offs, recommends one approach over another, or critiques a method
  create     — chunk proposes designing, building, or constructing something new

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHUNK TYPES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  definition  — defines or introduces a concept
  process     — describes steps, algorithms, or procedures
  comparison  — contrasts two or more methods or concepts
  example     — illustrates with a concrete case or application
  argument    — presents reasoning, evidence, or justification for a claim

*** CRITICAL — CONCEPTS AND KEYWORDS ***
"concepts" and "keywords" are the MOST IMPORTANT metadata fields. They represent the main ideas of the chunk and are used to match questions to topics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPTS — the core ideas of THIS specific chunk
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rules:
  - Each concept: 1–4 words, no more.
  - Concepts must be CENTRAL to this specific chunk — not background knowledge
    that is merely mentioned in passing or assumed as prior knowledge.
    Ask: "Is this chunk primarily ABOUT this concept, or does it just reference it?"
    Only list concepts the chunk actively explains or develops.
  - Extract the SPECIFIC idea discussed, not a generic category name.
  - Do NOT list results, outcomes, or meta-labels as concepts.
  - Maximum 5 concepts.
 
  BAD concepts (too generic, too vague, or meta-labels — do not use these):
    "convergence", "performance", "accuracy boost", "optimizer comparison",
    "deep neural networks", "machine learning",
    "gradient descent" (when only mentioned as background context, not the focus)
 
  GOOD concepts (specific, central to the chunk — use these as a style guide):
    "lookahead gradient", "exponential moving average", "neuron co-adaptation",
    "weight constraint", "adaptive learning rate decay", "bias correction term",
    "oscillation damping", "sparse weight pruning"
 
  Avoid using API names, class names, or function names (e.g. "tf.keras.metrics.Precision", "update_state") as concepts.
  Instead, extract the underlying idea or behavior (e.g. "state tracking", "batch aggregation", "metric computation").
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEYWORDS — specific technical terms from the chunk text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rules:
  - Keywords must appear LITERALLY in the chunk text (exact or near-exact match).
  - Keywords are used to build MCQ answer options and distractors — they must be
    specific, meaningful technical terms that a student should know.
  - Keywords must NOT duplicate or closely paraphrase anything in the concepts list.
    If "RMSProp" is already a concept, do not also list "RMSProp" as a keyword.
  - Do NOT include: code variable names, import paths, garbled OCR fragments,
    ℓ-norm symbols without specifying ℓ1 or ℓ2, or partial code strings.
  - Do NOT include vague generic terms: "algorithm", "method", "approach",
    "technique", "model", "network".
  - Maximum 6 keywords.
 
  SEPARATION EXAMPLE — chunk about momentum optimization:
    concepts  : ["momentum optimization", "local optima escape", "oscillation"]
    keywords  : ["velocity term", "friction coefficient", "bowl-shaped surface",
                 "exponentially decaying average"]
    CORRECT: "gradient descent" is background — it is NOT a concept for this chunk.
    CORRECT: keywords describe SPECIFIC TERMS from the text, not the same ideas as concepts.
 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION TARGETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rules:
  - Each question target must be fully answerable using ONLY the chunk text.
    Do NOT generate targets based on: the context fringe sentences, topics
    previewed in the last sentence of the chunk, or assumed background knowledge.
    If the chunk ends with "...and this leads to AdaGrad, which...", do NOT generate
    a target about AdaGrad — that content is not in this chunk.
  - Targets must correspond directly to the concepts — one target per concept is
    a good starting guide.
  - Vary the question form — do not use "What is X?" for every concept:
    "How does X differ from Y?", "Why does X cause Z?", "What happens when X is too high?",
    "Under what conditions would you choose X over Y?"
  - Minimum 2, maximum 4 targets per chunk.
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON array, one object per chunk, in input order.
No markdown, no explanation, no text before or after the JSON array.
Each object must have exactly these keys:
  chunk_id, usable, usability_reason, bloom_level, chunk_type, concepts, keywords, question_targets

question_targets must:
  - Be directly derived from the concepts
  - Reflect what meaningful questions can be asked from the chunk
  - Be clear, specific, and useful for MCQ generation
  
"usability_reason" — a short sentence explaining WHY the chunk is usable or not.

If usable is false, still fill the other fields as best you can.
question_targets must be a non-empty list even for unusable chunks (put ["N/A"]).
"""

# ── per-batch user prompt ─────────────────────────────────────────────────────
def build_user_prompt(batch: list[dict]) -> str:
    """
    Build the user-turn prompt for a batch of 1–2 chunks.
    Includes context fringe around each chunk.
    """
    parts = []
    for i, chunk in enumerate(batch, start=1):
        fringe = chunk.get("context_fringe", {})
        prev   = fringe.get("prev_sentence") if fringe else None
        nxt    = fringe.get("next_sentence")  if fringe else None

        context_block = ""
        if prev:
            context_block += f"[Previous context]: {prev}\n"
        if nxt:
            context_block += f"[Following context]: {nxt}\n"
        if context_block:
            context_block += "\n"

        # Truncate extremely long chunks before sending (guard against S2 outliers)
        text = chunk.get("text", "")
        words = text.split()
        if len(words) > MAX_CHUNK_WORDS:
            text = " ".join(words[:MAX_CHUNK_WORDS]) + " [truncated]"

        parts.append(
            f"--- CHUNK {i} (id: {chunk['chunk_id']}) ---\n"
            f"{context_block}"
            f"{text}\n"
        )

    joined = "\n".join(parts)
    return (
        f"Extract metadata for the following {len(batch)} chunk(s).\n\n"
        f"{joined}\n"
        f"Return a JSON array with {len(batch)} object(s), one per chunk, in order."
    )

# ── API call with retry ───────────────────────────────────────────────────────
def call_groq(client: Groq, batch: list[dict]) -> Optional[list[dict]]:
    """
    Call the Groq API for a batch of chunks.
    Returns a list of metadata dicts (one per chunk), or None on total failure.
    """
    user_prompt = build_user_prompt(batch)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,       # low temperature for structured extraction
                max_tokens=400,        # ~120 tokens × 2 chunks + buffer
                response_format={"type": "json_object"} if len(batch) == 1
                               else None,  # json_object only works for single object
            )
            raw = response.choices[0].message.content.strip()
            return _parse_response(raw, batch)

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                wait = BASE_BACKOFF ** attempt
                # Try to read retry-after from the exception message
                retry_match = re.search(r"retry.after[^\d]*(\d+(?:\.\d+)?)", err_str, re.IGNORECASE)
                if retry_match:
                    wait = max(wait, float(retry_match.group(1)) + 0.5)
                log.warning(f"Rate limit (attempt {attempt}/{MAX_RETRIES}). Waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                log.error(f"API error (attempt {attempt}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(BASE_BACKOFF * attempt)
                else:
                    return None

    return None

# ── response parsing ──────────────────────────────────────────────────────────
def _parse_response(raw: str, batch: list[dict]) -> Optional[list[dict]]:
    """
    Parse the raw LLM response into a list of validated metadata dicts.
    Handles both array and single-object JSON responses.
    """
    # Strip accidental markdown fences
    raw = re.sub(r"```json\s*|```\s*", "", raw).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract the first JSON array or object from the text
        array_match  = re.search(r"\[.*\]", raw, re.DOTALL)
        object_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if array_match:
            try:
                parsed = json.loads(array_match.group(0))
            except Exception:
                log.error(f"Could not parse JSON array from response: {raw[:200]}")
                return None
        elif object_match:
            try:
                parsed = json.loads(object_match.group(0))
            except Exception:
                log.error(f"Could not parse JSON object from response: {raw[:200]}")
                return None
        else:
            log.error(f"No JSON found in response: {raw[:200]}")
            return None

    # Normalise: always work with a list
    if isinstance(parsed, dict):
        # Model returned a single object for a 1-chunk call, or wrapped in a key
        # Common wrapping: {"results": [...]} or {"0": {...}, "1": {...}}
        if "results" in parsed:
            parsed = parsed["results"]
        elif all(str(i) in parsed for i in range(len(batch))):
            parsed = [parsed[str(i)] for i in range(len(batch))]
        else:
            parsed = [parsed]

    if not isinstance(parsed, list):
        log.error(f"Unexpected parsed type {type(parsed)}: {raw[:200]}")
        return None

    if len(parsed) != len(batch):
        log.warning(f"Response has {len(parsed)} items but batch has {len(batch)}. Padding with fallbacks.")
        while len(parsed) < len(batch):
            parsed.append(None)
        parsed = parsed[:len(batch)]

    # Validate and repair each item
    result = []
    for i, (item, chunk) in enumerate(zip(parsed, batch)):
        result.append(_validate_metadata(item, chunk))
    return result


def _validate_metadata(item: Optional[dict], chunk: dict) -> dict:
    """
    Ensure the metadata dict has all required fields with valid values.
    Falls back to safe defaults for any missing or invalid field.
    Normalises concepts (lowercase, strip, deduplicate) and enforces
    maximum list sizes to reduce noise.
    """
    VALID_BLOOM  = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
    VALID_TYPES  = {"definition", "process", "comparison", "example", "argument"}
    MAX_CONCEPTS = 6
    MAX_KEYWORDS = 8

    if not isinstance(item, dict):
        item = {}

    # chunk_id — always override with the actual chunk_id
    item["chunk_id"] = chunk["chunk_id"]

    # usable
    if not isinstance(item.get("usable"), bool):
        item["usable"] = True  # default to usable when unclear

    # usability_reason — always present, default to empty string
    if not isinstance(item.get("usability_reason"), str):
        item["usability_reason"] = ""

    # bloom_level
    if item.get("bloom_level") not in VALID_BLOOM:
        item["bloom_level"] = "understand"

    # chunk_type
    if item.get("chunk_type") not in VALID_TYPES:
        item["chunk_type"] = "definition"

    # concepts — do not allow empty; normalise & deduplicate
    if not isinstance(item.get("concepts"), list) or not item["concepts"]:
        item["concepts"] = ["general concept"]
    else:
        # Normalise: lowercase, strip whitespace, remove empties
        normalised = []
        seen = set()
        for c in item["concepts"]:
            if isinstance(c, str):
                normed = c.strip().lower()
                if normed and normed not in seen:
                    seen.add(normed)
                    normalised.append(normed)
        item["concepts"] = normalised if normalised else ["general concept"]
    # Limit to MAX_CONCEPTS
    item["concepts"] = item["concepts"][:MAX_CONCEPTS]

    # keywords — do not allow empty; limit size
    if not isinstance(item.get("keywords"), list) or not item["keywords"]:
        item["keywords"] = ["general"]
    else:
        # Strip whitespace and remove empties
        item["keywords"] = [k.strip() for k in item["keywords"] if isinstance(k, str) and k.strip()]
        if not item["keywords"]:
            item["keywords"] = ["general"]
    # Limit to MAX_KEYWORDS
    item["keywords"] = item["keywords"][:MAX_KEYWORDS]

    # question_targets — must be non-empty list
    if not isinstance(item.get("question_targets"), list) or not item["question_targets"]:
        item["question_targets"] = ["N/A"] if not item.get("usable") else ["General understanding"]

    return item

# ── JSONL helpers ──────────────────────────────────────────────────────────────
def load_jsonl(path: str) -> list[dict]:
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError as e:
                    log.warning(f"Skipping malformed line in {path}: {e}")
    return chunks


def load_existing_ids(path: str) -> set[str]:
    """Return the set of chunk_ids already present in the output file."""
    if not os.path.exists(path):
        return set()
    ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ids.add(json.loads(line)["chunk_id"])
                except Exception:
                    pass
    return ids

# ── main processing ────────────────────────────────────────────────────────────
def process_file(
    client: Groq,
    input_path: str,
    usable_output_path: str,
    not_usable_output_path: str,
) -> tuple[int, int, int]:
    """
    Process one JSONL file.
    Writes usable chunks to usable_output_path and
    not-usable chunks to not_usable_output_path.
    Returns (total_chunks, processed, usable_count).
    """
    chunks = load_jsonl(input_path)
    if not chunks:
        log.warning(f"No chunks found in {input_path}")
        return 0, 0, 0

    # Resume support: skip already-processed chunks (check both output files)
    done_ids = load_existing_ids(usable_output_path) | load_existing_ids(not_usable_output_path)
    pending  = [c for c in chunks if c["chunk_id"] not in done_ids]

    log.info(f"{Path(input_path).name}: {len(chunks)} total, {len(done_ids)} already done, {len(pending)} pending")

    if not pending:
        log.info("All chunks already processed. Nothing to do.")
        existing_usable = sum(
            1 for c in load_jsonl(usable_output_path) if c.get("metadata", {}).get("usable", True)
        )
        return len(chunks), 0, existing_usable

    os.makedirs(os.path.dirname(usable_output_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(not_usable_output_path) or ".", exist_ok=True)

    processed = 0
    usable    = 0
    errors    = 0

    with open(usable_output_path, "a", encoding="utf-8") as usable_f, \
         open(not_usable_output_path, "a", encoding="utf-8") as not_usable_f:
        # Process in batches
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start: batch_start + BATCH_SIZE]

            metadata_list = call_groq(client, batch)

            if metadata_list is None:
                log.error(f"Failed batch at position {batch_start}. Saving fallback records.")
                for chunk in batch:
                    record = _merge(chunk, _fallback_metadata(chunk["chunk_id"]))
                    # Fallback defaults to usable=True
                    usable_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    errors += 1
                continue

            for chunk, meta in zip(batch, metadata_list):
                record = _merge(chunk, meta)
                if meta.get("usable", True):
                    usable_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    usable += 1
                else:
                    not_usable_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                processed += 1

            # Respect TPM: 6,000 tokens/min → ~6 calls/min at 920 tok/call
            time.sleep(1.5)

            if (batch_start // BATCH_SIZE + 1) % 20 == 0:
                total_done = len(done_ids) + processed
                log.info(f"  Progress: {total_done}/{len(chunks)} chunks done ({usable} usable so far)")

    total_done = len(done_ids) + processed
    existing_usable = usable + sum(
        1 for c in load_jsonl(usable_output_path) if c["chunk_id"] in done_ids
        and c.get("metadata", {}).get("usable", True)
    )
    log.info(f"Done: {processed} new, {errors} errors, {total_done} total, usable so far: {existing_usable}")
    return len(chunks), processed, usable


def _merge(chunk: dict, meta: dict) -> dict:
    """
    Produce the final output record: original chunk fields + metadata sub-object.
    Input chunks contain only: file_id, chunk_id, text, context_fringe.
    """
    return {
        "file_id":        chunk.get("file_id"),
        "chunk_id":       chunk.get("chunk_id"),
        "text":           chunk.get("text"),
        "context_fringe": chunk.get("context_fringe"),
        "metadata": {
            "usable":            meta.get("usable", True),
            "usability_reason":  meta.get("usability_reason", ""),
            "bloom_level":       meta.get("bloom_level", "understand"),
            "chunk_type":        meta.get("chunk_type", "definition"),
            "concepts":          meta.get("concepts", ["general concept"]),
            "keywords":          meta.get("keywords", ["general"]),
            "question_targets":  meta.get("question_targets", ["General understanding"]),
        },
    }


def _fallback_metadata(chunk_id: str) -> dict:
    """Safe defaults used when an API call fails completely after all retries."""
    return {
        "chunk_id":         chunk_id,
        "usable":           True,   # keep by default — S4 will catch truly bad chunks
        "usability_reason": "",
        "bloom_level":      "understand",
        "chunk_type":       "definition",
        "concepts":         ["general concept"],
        "keywords":         ["general"],
        "question_targets": ["General understanding"],
    }

# ── CLI ────────────────────────────────────────────────────────────────────────
DEFAULT_INPUT = os.path.join("data", "global_chunks")


def parse_args():
    p = argparse.ArgumentParser(description="S3: metadata extraction for MCQ generation")
    p.add_argument("--input",  default=DEFAULT_INPUT,
                   help="Path to a .jsonl file or a directory of .jsonl files "
                        f"(default: {DEFAULT_INPUT})")
    p.add_argument("--output", required=True,
                   help="Path to output directory. Two sub-folders will be created: "
                        "usable/ and not_usable/")
    p.add_argument("--api-key", default=None,
                   help="Groq API key (defaults to GROQ_API_KEY env variable)")
    return p.parse_args()


def main():
    # Auto-load variables from app/.env (same directory as this script).
    load_dotenv_file(Path(__file__).with_name(".env"))

    args = parse_args()
    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Set GROQ_API_KEY environment variable or pass --api-key")

    client = Groq(api_key=api_key)

    input_path  = Path(args.input)
    output_path = Path(args.output)

    # Create the two output sub-folders
    usable_dir     = output_path / "usable"
    not_usable_dir = output_path / "not_usable"
    usable_dir.mkdir(parents=True, exist_ok=True)
    not_usable_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_dir():
        # Process all JSONL files in the input directory, skipping backups
        jsonl_files = sorted(
            f for f in input_path.glob("*.jsonl")
            if "backup" not in f.stem.lower()
        )
        if not jsonl_files:
            log.error(f"No .jsonl files found in {input_path} (excluding backups)")
            return

        grand_total = grand_processed = grand_usable = 0
        for jf in jsonl_files:
            usable_file     = usable_dir / (jf.stem + "_meta.jsonl")
            not_usable_file = not_usable_dir / (jf.stem + "_meta.jsonl")
            log.info(f"\n{'='*55}")
            log.info(f"Processing: {jf.name}")
            log.info(f"  → usable:     {usable_file}")
            log.info(f"  → not_usable: {not_usable_file}")
            log.info(f"{'='*55}")
            total, processed, usable = process_file(
                client, str(jf), str(usable_file), str(not_usable_file)
            )
            grand_total     += total
            grand_processed += processed
            grand_usable    += usable

        log.info(f"\n{'='*55}")
        log.info(f"ALL FILES DONE")
        log.info(f"  Total chunks   : {grand_total}")
        log.info(f"  Newly processed: {grand_processed}")
        log.info(f"  Usable         : {grand_usable}")
        log.info(f"  Output folders : {usable_dir}  |  {not_usable_dir}")
        log.info(f"{'='*55}")

    elif input_path.is_file():
        # Single file
        usable_file     = usable_dir / (input_path.stem + "_meta.jsonl")
        not_usable_file = not_usable_dir / (input_path.stem + "_meta.jsonl")
        process_file(client, str(input_path), str(usable_file), str(not_usable_file))

    else:
        log.error(f"Input path not found: {input_path}")


if __name__ == "__main__":
    main()