# app/quiz/quiz_generator.py
"""
Quiz MCQ generator — model inference, output parsing, validation, and post-processing.

This module handles:
  1. Calling the fine-tuned Qwen2.5-1.5B model (lazy-loaded on first use)
  2. Parsing the raw model output (JSON with fallback)
  3. Pydantic validation of the MCQ structure
  4. Option shuffling to eliminate positional bias
  5. Deduplication of near-duplicate MCQs
  6. Formatting the final API response

Model: mcq-bloom-qwen-merged  (local fine-tuned Qwen2.5-1.5B)
Loaded once on first call to avoid blocking startup.

Public API:
    from .quiz_generator import generate_mcqs
    results = generate_mcqs(model_inputs)
"""

import json
import random
import re
import logging
import os
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

log = logging.getLogger("quiz_generator")

# ═══════════════════════════════════════════════════════════════
# MODEL PATH — local fine-tuned Qwen2.5-1.5B
# ═══════════════════════════════════════════════════════════════

_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),          # .../app/quiz/
    "..", "..",                          # .../ai_service/
    "..",                                # .../Agentic-AI-Tutor/
    "mcq-bloom-qwen-merged",
)
_MODEL_PATH = os.path.normpath(_MODEL_PATH)

# Lazy-loaded singletons — populated on first call to _real_model_call()
_tokenizer = None
_model     = None


# Track model load time for reporting
_model_load_time: float = 0.0


def _load_model():
    """
    Load the fine-tuned Qwen2.5-1.5B tokenizer and model on first call.
    Subsequent calls are instant (singletons already set).
    """
    global _tokenizer, _model, _model_load_time
    if _tokenizer is not None:
        return

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    t0 = time.time()
    log.info("[QuizGen] Loading model from %s ...", _MODEL_PATH)
    _tokenizer = AutoTokenizer.from_pretrained(_MODEL_PATH)

    device_map = "auto"  # uses CUDA if available, falls back to CPU
    _model = AutoModelForCausalLM.from_pretrained(
        _MODEL_PATH,
        torch_dtype=torch.float16,   # Force 16-bit precision to fit in 4GB VRAM
        device_map=device_map,
    )
    _model.eval()
    _model_load_time = time.time() - t0

    # Detect device
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem  = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        device_info = f"GPU: {gpu_name} ({gpu_mem:.1f} GB VRAM)"
    else:
        device_info = "CPU (no CUDA GPU detected)"

    print(f"\n{'='*60}", flush=True)
    print(f"[QuizGen] Model loaded in {_model_load_time:.2f}s", flush=True)
    print(f"[QuizGen] Device: {device_info}", flush=True)
    print(f"{'='*60}\n", flush=True)
    log.info("[QuizGen] Model loaded successfully (device_map=%s)", device_map)


# ═══════════════════════════════════════════════════════════════
# PYDANTIC VALIDATION SCHEMA — FROM S4 NOTEBOOK
# ═══════════════════════════════════════════════════════════════

AnswerLabel = Literal["A", "B", "C", "D"]


class MCQSchema(BaseModel):
    """
    Strict Pydantic v2 schema for a single generated MCQ.

    Validates the structural integrity of the model's output before
    it reaches the API response. Any violation raises ValidationError
    which is caught and the slot is retried or skipped.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 8
    """
    question:    str = Field(..., min_length=10, max_length=400)
    options:     Dict[AnswerLabel, str]
    answer:      AnswerLabel
    explanation: str = Field(..., min_length=10)
    concept:     str = Field(..., min_length=2)
    bloom_level: str

    @field_validator("options")
    @classmethod
    def options_must_have_abcd(cls, v: dict) -> dict:
        if set(v.keys()) != {"A", "B", "C", "D"}:
            raise ValueError(
                f"options keys must be exactly A,B,C,D -- got {sorted(v.keys())}"
            )
        for lbl, text in v.items():
            if not text or not text.strip():
                raise ValueError(f"option {lbl} is empty")
        return v

    @field_validator("question")
    @classmethod
    def question_word_limit(cls, v: str) -> str:
        if len(v.split()) > 60:
            raise ValueError(f"question too long: {len(v.split())} words")
        return v.strip()

    @model_validator(mode="after")
    def answer_must_be_in_options(self) -> "MCQSchema":
        if self.answer not in self.options:
            raise ValueError(
                f"answer '{self.answer}' not found in options dict"
            )
        return self

    @model_validator(mode="after")
    def no_banned_option_phrases(self) -> "MCQSchema":
        banned = [
            "all of the above",
            "none of the above",
            "both a and",
            "both b and",
        ]
        for lbl, text in self.options.items():
            if any(b in text.lower() for b in banned):
                raise ValueError(f"option {lbl} contains banned phrase")
        return self


# ═══════════════════════════════════════════════════════════════
# JSON PARSING — FROM S4 NOTEBOOK
# ═══════════════════════════════════════════════════════════════

def _parse_model_output(raw_text: str) -> Optional[Dict]:
    """
    Parse raw model output into a dict. Handles:
      - Markdown fence stripping (```json ... ```)
      - Standard json.loads
      - Regex fallback to find JSON object in text

    Source: S4_MCQ_Pipeline_Final (2).ipynb, parse_json_safe()
    """
    text = raw_text.strip()

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )
        text = text.strip()

    # Automatically fix missing curly brackets if it looks like our JSON
    if '"question"' in text and '"options"' in text:
        if not text.startswith("{"):
            text = "{" + text
        if not text.endswith("}"):
            text = text + "}"

    # Attempt 1: direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed[0]
    except json.JSONDecodeError:
        pass

    # Attempt 2: find JSON object with regex
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Attempt 3: Regex plain-text parser
    # Extracts A), B), C), D) and Answer: when the model ignores JSON instructions
    # Strip markdown bold markers (**) so patterns like **Answer:** become Answer:
    plain = re.sub(r"\*\*", "", text)
    try:
        options = {}
        for opt in ["A", "B", "C", "D"]:
            # Looks for "A)", "A.", "a)", "a." at the start of a line
            pattern = rf"(?:^|\n)\s*{opt}[\)\.]\s*(.*?)(?=(?:^|\n)\s*[A-D][\)\.]|(?:^|\n)\s*(?:Answer|Explanation|Correct Answer):|$)"
            m = re.search(pattern, plain, re.DOTALL | re.IGNORECASE)
            if m:
                options[opt] = m.group(1).strip()
                
        ans_match = re.search(r"(?:^|\n)\s*(?:Answer|Correct Answer):\s*([A-D])", plain, re.IGNORECASE)
        
        if len(options) == 4 and ans_match:
            # Question is everything before A)
            q_part = re.split(r"(?:^|\n)\s*A[\)\.]", plain, flags=re.IGNORECASE)[0].strip()
            # Clean markdown labels from the question (e.g. "Question:", "Options:")
            q_part = re.sub(r"^(?:Question|Options):\s*", "", q_part, flags=re.IGNORECASE | re.MULTILINE).strip()
            q_part = re.sub(r"\s*(?:Options):\s*$", "", q_part, flags=re.IGNORECASE).strip()
            
            # Explanation is anything after Answer: X if there is an Explanation: tag
            exp_match = re.search(r"(?:^|\n)\s*(?:Explanation|Justification):\s*(.*?)(?=(?:^|\n)\s*(?:Concept|Bloom Level):|$)", plain, re.DOTALL | re.IGNORECASE)
            exp = exp_match.group(1).strip() if exp_match else None
            
            # Concept and Bloom Level tags
            concept_match = re.search(r"(?:^|\n)\s*Concept:\s*(.*?)(?=(?:^|\n)\s*(?:Bloom Level|Explanation):|$)", plain, re.DOTALL | re.IGNORECASE)
            bloom_match = re.search(r"(?:^|\n)\s*Bloom Level:\s*(.*?)(?=(?:^|\n)\s*(?:Concept|Explanation):|$)", plain, re.DOTALL | re.IGNORECASE)
                
            result = {
                "question": q_part,
                "options": options,
                "answer": ans_match.group(1).upper(),
                "concept": concept_match.group(1).strip() if concept_match else "extracted_concept",
                "bloom_level": bloom_match.group(1).strip() if bloom_match else "understand"
            }
            if exp:
                result["explanation"] = exp
            log.info("[QuizGen] Successfully parsed plain-text format into JSON (explanation=%s, concept=%s)",
                     "found" if exp else "MISSING", "found" if concept_match else "MISSING")
            return result
    except Exception as e:
        log.warning("[QuizGen] Regex parser error: %s", e)

    log.warning("[QuizGen] Could not parse model output as JSON. Raw output was:\n%s", raw_text)
    return None


# ═══════════════════════════════════════════════════════════════
# OPTION SHUFFLING — FROM S4 NOTEBOOK
# ═══════════════════════════════════════════════════════════════

_LABELS = ("A", "B", "C", "D")


def _shuffle_options(mcq: Dict) -> Dict:
    """
    Randomly permute option texts across A/B/C/D labels.
    Remaps answer key to new positions.
    Returns a new dict — does NOT mutate the input.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 5, shuffle_options()
    """
    mcq = dict(mcq)
    options = mcq.get("options", {})
    answer = mcq.get("answer", "")

    if not isinstance(options, dict) or len(options) != 4:
        return mcq

    correct_text = options.get(answer, "")
    texts = list(options.values())
    random.shuffle(texts)
    new_options = dict(zip(_LABELS, texts))

    new_answer = next(
        (lbl for lbl, txt in new_options.items() if txt == correct_text),
        answer,
    )

    mcq["options"] = new_options
    mcq["answer"] = new_answer
    return mcq


# ═══════════════════════════════════════════════════════════════
# REAL MODEL INFERENCE — Qwen2.5-1.5B fine-tuned (mcq-bloom-qwen-merged)
# ═══════════════════════════════════════════════════════════════

def _real_model_call(system_prompt: str, user_prompt: str, attempt: int = 1) -> str:
    """
    Run MCQ inference with the merged fine-tuned Qwen2.5-1.5B model.

    Uses tokenizer.apply_chat_template() to match the exact ShareGPT
    format the model was trained on (system + user turns, then
    add_generation_prompt=True to trigger the assistant turn).

    The model is lazy-loaded on the first call.
    """
    import torch

    _load_model()  # no-op after first call

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    # Apply the Qwen chat template — matches training format exactly
    text = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _tokenizer([text], return_tensors="pt").to(_model.device)

    # Determine generation parameters based on attempt
    do_sample = False
    temperature = None
    top_p = None
    if attempt == 2:
        do_sample = True
        temperature = 0.7
        top_p = 0.9

    with torch.no_grad():
        out_ids = _model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=do_sample,
            temperature=temperature,
            top_p=top_p,
            top_k=None,
        )

    # Strip input tokens → keep only the newly generated tokens
    new_ids = out_ids[0][inputs.input_ids.shape[1]:]
    return _tokenizer.decode(new_ids, skip_special_tokens=True)


# ═══════════════════════════════════════════════════════════════
# MCQ DEDUPLICATION — question similarity + option overlap
# ═══════════════════════════════════════════════════════════════

def _question_similarity(q1: str, q2: str) -> float:
    """
    SequenceMatcher ratio between two question stems (0.0 – 1.0).
    Case-insensitive and strip-normalised.
    """
    return SequenceMatcher(
        None, q1.lower().strip(), q2.lower().strip()
    ).ratio()


def _option_overlap_score(mcq_a: Dict, mcq_b: Dict) -> float:
    """
    Fraction of option texts shared between two MCQs (0.0 – 1.0).
    Catches cases where the stem is reworded but the distractors are identical.
    """
    opts_a = {opt["text"].lower().strip() for opt in mcq_a.get("options", [])}
    opts_b = {opt["text"].lower().strip() for opt in mcq_b.get("options", [])}
    if not opts_a or not opts_b:
        return 0.0
    return len(opts_a & opts_b) / min(len(opts_a), len(opts_b))


def _deduplicate_mcqs(
    mcqs: List[Dict],
    question_threshold: float = 0.92,
    option_threshold:   float = 0.75,
) -> List[Dict]:
    """
    Remove near-duplicate MCQs using OR logic on two signals:
      1. Question stem similarity >= question_threshold
      2. Option text overlap    >= option_threshold

    The FIRST occurrence is kept; later duplicates are dropped.
    Order from assign_slots() is preserved (named > reuse > inferred),
    so higher-priority slots survive.
    """
    unique: List[Dict] = []
    for mcq in mcqs:
        q_text = mcq.get("question_text", "")
        is_dup = False
        for existing in unique:
            if _question_similarity(q_text, existing.get("question_text", "")) >= question_threshold:
                is_dup = True
                break
            if _option_overlap_score(mcq, existing) >= option_threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(mcq)
    return unique


# ═══════════════════════════════════════════════════════════════
# RESPONSE FORMATTING
# ═══════════════════════════════════════════════════════════════

def _format_response(mcq: Dict, slot_meta: Dict) -> Dict:
    """
    Assemble the final API response object.

    concept and bloom_level come from the INPUT (slot_metadata),
    NOT from the model output.
    """
    options = mcq.get("options", {})
    options_list = [
        {"label": lbl, "text": options.get(lbl, "")}
        for lbl in _LABELS
        if lbl in options
    ]

    return {
        "question_text":  mcq.get("question", ""),
        "options":        options_list,
        "correct_option": mcq.get("answer", ""),
        "explanation":    mcq.get("explanation", ""),
        # From input, NOT from model output
        "concept":        slot_meta.get("concept", ""),
        "bloom_level":    slot_meta.get("bloom_level", ""),
        "chunk_id":       slot_meta.get("chunk_id", ""),
        "document_id":    slot_meta.get("document_id", ""),
    }


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def _try_generate_one(system_prompt: str, user_prompt: str, label: str, attempt: int, slot_meta: dict = None) -> tuple:
    """
    Attempt a single model call → parse → validate cycle.
    Returns (mcq_dict, raw_output, parsed, error_status, error_msg).
    On success: mcq_dict is populated, error_status is None.
    On failure: mcq_dict is None, error_status/error_msg describe the issue.
    """
    try:
        raw_output = _real_model_call(system_prompt, user_prompt, attempt=attempt)
    except Exception as e:
        return None, None, None, "failed_model_call", str(e)

    parsed = _parse_model_output(raw_output)
    if parsed is None:
        return None, raw_output, None, "failed_parsing", "JSON parse failed"

    if slot_meta is not None:
        if "bloom_level" not in parsed and "bloom_level" in slot_meta:
            parsed["bloom_level"] = slot_meta["bloom_level"]
        if "concept" not in parsed and "concept" in slot_meta:
            parsed["concept"] = slot_meta["concept"]

    try:
        validated = MCQSchema.model_validate(parsed)
        mcq_dict = validated.model_dump()
        return mcq_dict, raw_output, parsed, None, None
    except Exception as e:
        return None, raw_output, parsed, "failed_validation", str(e)


def generate_mcqs(model_inputs: List[Dict]) -> List[Dict]:
    """
    Generate MCQs from model-ready input dicts.

    For each input:
      1. Call the fine-tuned Qwen2.5-1.5B model
      2. Parse JSON output
      3. Validate with Pydantic
      4. If step 2 or 3 fails → RETRY once
      5. Shuffle options
      6. Format response with slot metadata

    After all slots are processed, near-duplicate MCQs are removed
    (question similarity >= 0.80 OR option overlap >= 0.75).

    Failed slots are logged and skipped — only valid MCQs are returned.

    Args:
        model_inputs: List of dicts from prepare_all_model_inputs().
                      Each has: system_prompt, user_prompt, slot_metadata.

    Returns:
        List of formatted MCQ response dicts.
    """
    import torch

    total_start = time.time()
    results: List[Dict] = []
    debug_logs: List[Dict] = []
    slot_times: List[float] = []

    # Detect device info
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem  = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        device_str = f"GPU: {gpu_name} ({gpu_mem:.1f} GB VRAM)"
    else:
        device_str = "CPU (no CUDA GPU detected)"

    # ANSI color codes for prettier terminal output
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"

    print(f"\n{CYAN}{'─'*60}{RESET}", flush=True)
    print(f"{BOLD}[QuizGen]{RESET} Starting generation of {BOLD}{len(model_inputs)}{RESET} slots", flush=True)
    print(f"{BOLD}[QuizGen]{RESET} Device: {CYAN}{device_str}{RESET}", flush=True)
    print(f"{CYAN}{'─'*60}{RESET}", flush=True)

    for i, inp in enumerate(model_inputs):
        slot_start = time.time()
        system_prompt = inp["system_prompt"]
        user_prompt = inp["user_prompt"]
        slot_meta = inp["slot_metadata"]

        bloom_lvl = slot_meta.get("bloom_level").upper()
        concept = slot_meta.get("concept")
        
        # Real-time progress print (starts line, doesn't end it yet)
        progress_prefix = f"[{i+1:02d}/{len(model_inputs):02d}]"
        print(f"{CYAN}{progress_prefix}{RESET} {BOLD}{bloom_lvl:<8}{RESET} | {concept[:30]:<30} ... ", end="", flush=True)

        label = (
            f"chunk={slot_meta.get('chunk_id', '?')[:8]} "
            f"concept='{slot_meta.get('concept', '?')}' "
            f"bloom={slot_meta.get('bloom_level', '?')}"
        )

        log_entry = {
            "slot": i,
            "chunk_id": slot_meta.get("chunk_id"),
            "concept": slot_meta.get("concept"),
            "bloom": slot_meta.get("bloom_level"),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_output": None,
            "status": "pending",
            "error": None,
            "attempts": 1,
        }

        # ── Attempt 1 ──
        mcq_dict, raw_output, parsed, err_status, err_msg = _try_generate_one(
            system_prompt, user_prompt, label, attempt=1, slot_meta=slot_meta
        )
        log_entry["raw_output"] = raw_output

        # ── Attempt 2 (retry) if first attempt failed ──
        if mcq_dict is None:
            print(f"{YELLOW}Retrying...{RESET} ", end="", flush=True)
            log.info("[QuizGen] Slot %d (%s): attempt 1 failed (%s), retrying...", i, label, err_status)
            mcq_dict2, raw_output2, parsed2, err_status2, err_msg2 = _try_generate_one(
                system_prompt, user_prompt, label, attempt=2, slot_meta=slot_meta
            )
            log_entry["attempts"] = 2
            log_entry["retry_raw_output"] = raw_output2

            if mcq_dict2 is not None:
                # Retry succeeded!
                mcq_dict = mcq_dict2
                raw_output = raw_output2
                parsed = parsed2
                err_status = None
                err_msg = None
                # We intentionally do NOT overwrite log_entry["raw_output"] here
                # so that the log file preserves Attempt 1's output.
                log.info("[QuizGen] Slot %d (%s): retry SUCCEEDED", i, label)
            else:
                # Both attempts failed — use error info from attempt 2
                err_status = err_status2
                err_msg = err_msg2
                parsed = parsed2
                raw_output = raw_output2

        slot_elapsed = time.time() - slot_start
        slot_times.append(slot_elapsed)

        if mcq_dict is None:
            # Final failure after retry
            print(f"{RED}FAILED{RESET} ({err_status})", flush=True)
            log.warning("[QuizGen] Slot %d (%s): FAILED after 2 attempts (%s)", i, label, err_status)
            log_entry["status"] = err_status
            log_entry["error"] = err_msg
            if parsed is not None:
                log_entry["parsed_output"] = parsed
            debug_logs.append(log_entry)
            continue

        # Shuffle options
        mcq_dict = _shuffle_options(mcq_dict)

        # Format response
        response = _format_response(mcq_dict, slot_meta)
        results.append(response)

        log_entry["status"] = "success"
        debug_logs.append(log_entry)
        print(f"{GREEN}SUCCESS{RESET} ({slot_elapsed:.1f}s)", flush=True)
        log.info("[QuizGen] Slot %d (%s): SUCCESS (%.1fs)", i, label, slot_elapsed)

    # Deduplicate
    before_dedup = len(results)
    results = _deduplicate_mcqs(results)
    if len(results) < before_dedup:
        log.info(
            "[QuizGen] Dedup: %d → %d MCQs (removed %d duplicates)",
            before_dedup, len(results), before_dedup - len(results),
        )

    # ── Timing summary ──
    def format_time(seconds: float) -> str:
        if seconds >= 60:
            m = int(seconds // 60)
            s = seconds % 60
            return f"{m}m {s:.2f}s"
        return f"{seconds:.2f}s"

    total_elapsed = time.time() - total_start
    avg_slot = sum(slot_times) / len(slot_times) if slot_times else 0
    fastest = min(slot_times) if slot_times else 0
    slowest = max(slot_times) if slot_times else 0
    success_count = sum(1 for d in debug_logs if d["status"] == "success")
    failed_count  = len(debug_logs) - success_count

    print(f"\n{CYAN}{'='*60}{RESET}", flush=True)
    print(f"{BOLD}  Timing Summary{RESET}", flush=True)
    print(f"{CYAN}{'─'*60}{RESET}", flush=True)
    print(f"  Device:         {CYAN}{device_str}{RESET}", flush=True)
    print(f"  Model load:     {format_time(_model_load_time)}", flush=True)
    print(f"  Total run:      {format_time(total_elapsed)}", flush=True)
    print(f"  Avg per slot:   {format_time(avg_slot)}", flush=True)
    print(f"  Fastest slot:   {format_time(fastest)}", flush=True)
    print(f"  Slowest slot:   {format_time(slowest)}", flush=True)
    print(f"{CYAN}{'─'*60}{RESET}", flush=True)
    print(f"  Slots:          {BOLD}{len(model_inputs)}{RESET} total", flush=True)
    print(f"  Success:        {GREEN}{BOLD}{success_count}{RESET}", flush=True)
    print(f"  Failed:         {RED}{BOLD}{failed_count}{RESET}", flush=True)
    print(f"  MCQs returned:  {CYAN}{BOLD}{len(results)}{RESET} (after dedup)", flush=True)
    print(f"{CYAN}{'='*60}{RESET}\n", flush=True)

    # ── Write logs to file (overwrite per run) ──
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.normpath(os.path.join(log_dir, "quiz_generation_log.json"))

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(debug_logs, f, indent=2, ensure_ascii=False)

    except Exception as e:
        log.error("[QuizGen] Failed to write debug log: %s", e)

    return results
