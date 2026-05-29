# app/quiz/quiz_generator.py
"""
Quiz MCQ generator — model inference, output parsing, validation, and post-processing.

This module handles:
  1. Calling the fine-tuned model (MOCKED for now)
  2. Parsing the raw model output (JSON with fallback)
  3. Pydantic validation of the MCQ structure
  4. Option shuffling to eliminate positional bias
  5. Formatting the final API response

The mock will be replaced with the real Qwen2.5 model later.
Only ONE function (_mock_model_call) needs to change when the model is added.

Public API:
    from .quiz_generator import generate_mcqs
    results = generate_mcqs(model_inputs)
"""

import json
import random
import re
import logging
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

log = logging.getLogger("quiz_generator")


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
    question:    str = Field(..., min_length=10, max_length=500)
    options:     Dict[AnswerLabel, str]
    answer:      AnswerLabel
    explanation: str = Field(..., min_length=10)

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

    log.warning("[QuizGen] Could not parse model output as JSON")
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
# MOCK MODEL — TEMPORARY UNTIL REAL MODEL IS LOADED
# ═══════════════════════════════════════════════════════════════

def _mock_model_call(system_prompt: str, user_prompt: str) -> str:
    """
    Temporary mock model. Returns a structurally valid MCQ JSON string.

    This function will be replaced with the real model inference:
        tokenizer.apply_chat_template() + model.generate()

    The mock extracts concept and chunk_type from the user prompt
    to generate contextually relevant (but fake) MCQ content.
    """
    # Extract concept from the prompt for realistic mock output
    concept_match = re.search(r'\[FOCUS CONCEPT\]:\s*(.+)', user_prompt)
    concept = concept_match.group(1).strip() if concept_match else "the concept"

    # Extract chunk_type from the prompt
    type_match = re.search(r'\[CHUNK TYPE\]:\s*(.+)', user_prompt)
    chunk_type = type_match.group(1).strip() if type_match else "definition"

    # Extract bloom level from the prompt
    bloom_match = re.search(r'\[BLOOM LEVEL\]:\s*(.+)', user_prompt)
    bloom = bloom_match.group(1).strip() if bloom_match else "understand"

    # Generate a mock MCQ that passes validation
    mock_mcq = {
        "question": f"Which of the following best describes {concept} in the context of this material?",
        "options": {
            "A": f"{concept} is a method used for optimizing gradient computations in neural networks",
            "B": f"{concept} is a technique for reducing overfitting by randomly dropping neurons during training",
            "C": f"{concept} is a process of adjusting model parameters based on the error signal propagated backwards",
            "D": f"{concept} is an approach for normalizing input features to improve convergence speed",
        },
        "answer": "C",
        "explanation": f"{concept} involves adjusting model parameters based on the error signal, which is computed during the backward pass through the network layers.",
    }

    return json.dumps(mock_mcq, ensure_ascii=False)


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

def generate_mcqs(model_inputs: List[Dict]) -> List[Dict]:
    """
    Generate MCQs from model-ready input dicts.

    For each input:
      1. Call the model (mocked for now)
      2. Parse JSON output
      3. Validate with Pydantic
      4. Shuffle options
      5. Format response with slot metadata

    Failed slots are logged and skipped — only valid MCQs are returned.

    Args:
        model_inputs: List of dicts from prepare_all_model_inputs().
                      Each has: system_prompt, user_prompt, slot_metadata.

    Returns:
        List of formatted MCQ response dicts.
    """
    results: List[Dict] = []

    for i, inp in enumerate(model_inputs):
        system_prompt = inp["system_prompt"]
        user_prompt = inp["user_prompt"]
        slot_meta = inp["slot_metadata"]

        label = (
            f"chunk={slot_meta.get('chunk_id', '?')[:8]} "
            f"concept='{slot_meta.get('concept', '?')}' "
            f"bloom={slot_meta.get('bloom_level', '?')}"
        )

        try:
            # Step 1: Call model (mocked)
            raw_output = _mock_model_call(system_prompt, user_prompt)

            # Step 2: Parse JSON
            parsed = _parse_model_output(raw_output)
            if parsed is None:
                log.warning("[QuizGen] Slot %d (%s): JSON parse failed, skipping", i, label)
                continue

            # Step 3: Pydantic validation
            try:
                validated = MCQSchema.model_validate(parsed)
                mcq_dict = validated.model_dump()
            except Exception as e:
                log.warning(
                    "[QuizGen] Slot %d (%s): validation failed: %s",
                    i, label, str(e)[:150],
                )
                continue

            # Step 4: Shuffle options
            mcq_dict = _shuffle_options(mcq_dict)

            # Step 5: Format response
            response = _format_response(mcq_dict, slot_meta)
            results.append(response)

            log.info("[QuizGen] Slot %d (%s): SUCCESS", i, label)

        except Exception as e:
            log.error(
                "[QuizGen] Slot %d (%s): unexpected error: %s",
                i, label, str(e)[:200],
            )

    log.info(
        "[QuizGen] Generated %d MCQs from %d slots",
        len(results), len(model_inputs),
    )
    return results
