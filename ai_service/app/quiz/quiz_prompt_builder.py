# app/quiz/quiz_prompt_builder.py
"""
Quiz prompt builder — prepares model-ready inputs for the fine-tuned MCQ model.

This module bridges the gap between the quiz pipeline's enriched chunk data
and the exact input format the fine-tuned Qwen2.5-1.5B model was trained on.

It reproduces the EXACT prompt structure from the SFT training pipeline:
  - SFT_SYSTEM_PROMPT  (static, identical across all calls)
  - build_user_prompt_conditioned()  (dynamic, per-slot)
  - assign_slots()  (3–4 MCQ slots per chunk based on concept count)
  - clean_concepts()  (validates concepts, NLP fallback if < 2)

Source notebooks (reference only — code is adapted for production):
  - S4_MCQ_Pipeline_Final (2).ipynb  — concept cleaning, slot assignment
  - quiz-ft-v4-with-evaluation.ipynb — SFT prompts, user prompt builder

Public API:
    from .quiz_prompt_builder import prepare_all_model_inputs
    model_inputs = prepare_all_model_inputs(chunks, mcqs_per_chunk=3)
"""

import re
from typing import Dict, List, Optional
from collections import Counter


# ═══════════════════════════════════════════════════════════════
# CONSTANTS — COPIED VERBATIM FROM THE SFT TRAINING NOTEBOOK
# ═══════════════════════════════════════════════════════════════

# The system prompt MUST match the training format exactly (char-for-char).
# Source: quiz-ft-v4-with-evaluation.ipynb, Section 5, SFT_SYSTEM_PROMPT
SFT_SYSTEM_PROMPT = "\n".join([
    # -- Persona & core behavior
    "You are an expert educational content designer for Bloom's Taxonomy-aligned assessment.",
    "Generate multiple-choice questions from educational text.",
    "Return ONLY valid JSON. No markdown fences, preambles, or commentary.",
    "",

    # -- Bloom levels (compressed)
    "## BLOOM LEVELS",
    "remember: recall facts | understand: explain meaning | apply: use in scenario",
    "analyze: compare/reason | evaluate: justify decision | create: design/propose",
    "",

    # -- Chunk type forms (compressed)
    "## CHUNK TYPE FORMS",
    "definition: explain concept | process: steps/sequence | comparison: differences",
    "example: real case | argument: evaluate claim",
    "",

    # -- Grounding rule (highest priority)
    "## GROUNDING (highest priority)",
    "- Correct answer MUST be explicitly stated in or directly inferable from the chunk.",
    "- Do NOT use external knowledge.",
    "",

    # -- MCQ quality rules
    "## MCQ RULES",
    "- Exactly 4 options: A, B, C, D. Exactly ONE correct answer.",
    "- Forbidden: 'All of the above', 'None of the above', 'Both A and B'.",
    "- Options must be similar in length (±25-30%) and share the same grammatical structure.",
    "- Options must be mutually exclusive. Do NOT embed the correct answer text in the question.",
    "",

    # -- Distractor rules
    "## DISTRACTORS",
    "- Use the keywords list to craft plausible distractors.",
    "- All 3 wrong options must belong to the same category/domain as the correct answer.",
    "- Distractors must be plausible to a student who skipped the chunk.",
    "",

    # -- Question phrasing
    "## QUESTION PHRASING",
    '- Do NOT say "according to the text", "based on the chunk", or "as stated above".',
    "- Question stem must be self-contained and <= 50 words.",
    "",

    "- You MUST complete the JSON fully. Do not stop mid-output.",
    "- Ensure all 4 options A,B,C,D are present before finishing.",
    "",

    "## EXPLANATION RULES",
    "- Do NOT mention option letters (A, B, C, D).",
    "- Refer to the answer by its content, not its position.",
    "- Do NOT use phrases like 'according to the text' or 'according to the chunk'.",
    "- Justify the correct concept clearly using its meaning.",
    "",

    # -- Output format (single MCQ)
    "## OUTPUT FORMAT -- return ONLY this JSON object:",
    "{",
    '  "question": "<full question stem>",',
    '  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},',
    '  "answer": "<A|B|C|D>",',
    '  "explanation": "<1-2 sentences: why correct, referencing chunk>",',
    '  "concept": "<the concept this question tests>",',
    '  "bloom_level": "<bloom level>"',
    "}",
])


# Per-bloom instruction line injected into the user prompt.
# Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 7
BLOOM_INSTRUCTION: Dict[str, str] = {
    "remember":   "Generate a RECALL question. Test a fact, definition, or named item directly stated in the text.",
    "understand": "Generate an INTERPRETATION question. Test whether the student can explain or paraphrase.",
    "apply":      "Generate a SCENARIO question. Place the concept in a new, concrete situation.",
    "analyze":    "Generate a COMPARISON or REASONING question. The stem MUST compare two items or ask for a cause.",
    "evaluate":   "Generate a JUDGMENT question. Ask the student to choose and justify.",
    "create":     "Generate a DESIGN or SYNTHESIS question.",
}


# Per-chunk-type instruction line injected into the user prompt.
# Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 7
CHUNK_TYPE_FORM: Dict[str, str] = {
    "definition": "Use 'What is / Which best describes' style.",
    "process":    "Use 'What happens when / Which step follows' style.",
    "comparison": "Use 'How does X differ from Y / Which distinguishes' style.",
    "example":    "Use a scenario-based style embedding the concept in a concrete case.",
    "argument":   "Require evaluating a claim, premise, or conclusion.",
}


# Bloom level ordering for _next_bloom() progression.
# Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 4
_BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


# Concept cleaning constants.
# Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 4
_MIN_CONCEPT_LENGTH = 3
_MIN_CONCEPTS_NEEDED = 2


# ═══════════════════════════════════════════════════════════════
# CONCEPT CLEANING — FROM S4 NOTEBOOK
# ═══════════════════════════════════════════════════════════════

def _extract_concepts_from_text(text: str, max_concepts: int = 4) -> List[str]:
    """
    Lightweight NLP-free concept extraction using word-bigram frequency.
    Falls back to longest unique non-stopword words.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 4
    """
    clean = re.sub(r"[^a-zA-Z0-9\s\-]", " ", text)
    words = clean.split()
    candidates: List[str] = []
    for i in range(len(words) - 1):
        w1, w2 = words[i].lower(), words[i + 1].lower()
        if len(w1) >= 4 and len(w2) >= 4:
            candidates.append(f"{w1} {w2}")

    freq = Counter(candidates)
    top = [c for c, _ in freq.most_common(max_concepts * 2)]

    if not top:
        stopwords = {
            "this", "that", "with", "from", "have", "they", "been", "were",
            "their", "into", "also", "than", "when", "what", "which", "will",
            "about", "more",
        }
        top = sorted(
            {w.lower() for w in words if len(w) >= 5 and w.lower() not in stopwords},
            key=len,
            reverse=True,
        )[:max_concepts]

    return top[:max_concepts]


def clean_concepts(concepts: List[str], chunk_text: str) -> List[str]:
    """
    Validate concept list. Triggers NLP fallback if concepts are
    missing, too short, or fewer than MIN_CONCEPTS_NEEDED.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 4
    """
    cleaned = [
        c.strip()
        for c in concepts
        if isinstance(c, str) and len(c.strip()) >= _MIN_CONCEPT_LENGTH
    ]

    if len(cleaned) < _MIN_CONCEPTS_NEEDED:
        extracted = _extract_concepts_from_text(chunk_text, max_concepts=4)
        seen: set = set()
        merged: List[str] = []
        for c in cleaned + extracted:
            key = c.lower()
            if key not in seen:
                seen.add(key)
                merged.append(c)
        cleaned = merged[:4]

    return cleaned


# ═══════════════════════════════════════════════════════════════
# SLOT ASSIGNMENT — FROM S4 NOTEBOOK
# ═══════════════════════════════════════════════════════════════

def _next_bloom(bloom: str, step: int = 1) -> str:
    """
    Advance Bloom level by `step` tiers, capped at 'create'.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 4
    """
    idx = _BLOOM_ORDER.index(bloom) if bloom in _BLOOM_ORDER else 2
    return _BLOOM_ORDER[min(len(_BLOOM_ORDER) - 1, idx + step)]


def assign_slots(
    concepts: List[str],
    bloom_level: str,
    max_slots: int = 4,
) -> List[Dict[str, str]]:
    """
    Build MCQ slots dynamically based on available concept count.

    Rules (from S4 notebook):
      concepts == 0  -> 2 inferred slots
      concepts == 1  -> concept@bloom + concept@bloom+1 + inferred = 3 slots
      concepts == 2  -> c1@bloom + c2@bloom+1 + inferred            = 3 slots
      concepts >= 3  -> c1@bloom + c2@bloom+1 + c3@bloom+2 + inferred = 4 slots

    The max_slots parameter caps the number of slots returned,
    implementing the mcqs_per_chunk controller from the API.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 4
    """
    bloom = bloom_level.lower() if bloom_level in _BLOOM_ORDER else "understand"
    n = len(concepts)

    slots: List[Dict[str, str]] = []

    if n == 0:
        # Edge case — no concepts at all; use 2 inferred slots
        slots = [
            {"concept": "inferred", "bloom_level": bloom,             "slot_type": "inferred"},
            {"concept": "inferred", "bloom_level": _next_bloom(bloom), "slot_type": "inferred"},
        ]
    elif n == 1:
        # Same concept, two different Bloom depths, then inferred
        slots = [
            {"concept": concepts[0], "bloom_level": bloom,                "slot_type": "named"},
            {"concept": concepts[0], "bloom_level": _next_bloom(bloom, 1), "slot_type": "reuse"},
            {"concept": "inferred",  "bloom_level": bloom,                "slot_type": "inferred"},
        ]
    elif n == 2:
        slots = [
            {"concept": concepts[0], "bloom_level": bloom,                "slot_type": "named"},
            {"concept": concepts[1], "bloom_level": _next_bloom(bloom, 1), "slot_type": "named"},
            {"concept": "inferred",  "bloom_level": bloom,                "slot_type": "inferred"},
        ]
    else:
        # 3 or more concepts — use top 3
        slots = [
            {"concept": concepts[0], "bloom_level": bloom,                "slot_type": "named"},
            {"concept": concepts[1], "bloom_level": _next_bloom(bloom, 1), "slot_type": "named"},
            {"concept": concepts[2], "bloom_level": _next_bloom(bloom, 2), "slot_type": "named"},
            {"concept": "inferred",  "bloom_level": bloom,                "slot_type": "inferred"},
        ]

    # Apply the mcqs_per_chunk cap
    return slots[:max_slots]


# ═══════════════════════════════════════════════════════════════
# PROMPT CONSTRUCTION — FROM FT NOTEBOOK
# ═══════════════════════════════════════════════════════════════

def _build_concept_block(slot: Dict[str, str], all_concepts: List[str]) -> str:
    """
    Return the concept-constraint paragraph for a single slot.

    Source: S4_MCQ_Pipeline_Final (2).ipynb, Section 7, _build_concept_block()
    """
    slot_concept = slot["concept"]
    slot_type = slot.get("slot_type", "named")

    if slot_type == "inferred":
        already_used = ", ".join(f'"{c}"' for c in all_concepts) or "(none)"
        return (
            "CONCEPT CONSTRAINT -- INFERRED\n"
            "The question must test a NEW idea found in the chunk that is NOT any of these:\n"
            f"  Already covered: {already_used}\n"
            "Identify a distinct, meaningful concept from the text and write your question about it.\n"
            'Set the "concept" field to the NAME of the new concept you chose (NOT the word "inferred").'
        )
    elif slot_type == "reuse":
        return (
            "CONCEPT CONSTRAINT -- SAME CONCEPT, DIFFERENT ANGLE\n"
            f'Concept to test: "{slot_concept}"\n'
            "This concept was already tested at a lower Bloom level.\n"
            "You MUST test a DIFFERENT ASPECT or IMPLICATION of this concept.\n"
            "Do NOT ask the same type of question"
        )
    else:
        return (
            "CONCEPT CONSTRAINT\n"
            f'The question MUST focus specifically on: "{slot_concept}"\n'
            "Do NOT drift into other concepts. The entire question, correct answer, and distractors\n"
            f'must be directly connected to "{slot_concept}" as discussed in the chunk.'
        )


def build_model_input(
    chunk: Dict,
    slot: Dict[str, str],
    all_concepts: List[str],
) -> Dict:
    """
    Build the exact model input matching the SFT training format.

    Returns a dict with:
        system_prompt  — SFT_SYSTEM_PROMPT (static)
        user_prompt    — conditioned user prompt (dynamic, per-slot)
        slot_metadata  — concept, bloom_level, slot_type, chunk_id, document_id

    The user_prompt structure matches build_user_prompt_conditioned()
    from the FT notebook exactly.

    Source: quiz-ft-v4-with-evaluation.ipynb, Section 5
    """
    text = chunk.get("chunk_text", "").strip()
    chunk_type = chunk.get("chunk_type", "definition").lower()
    keywords = chunk.get("keywords", [])
    prev_s = (chunk.get("context_prev_sentence") or "").strip()
    next_s = (chunk.get("context_next_sentence") or "").strip()

    slot_bloom = slot["bloom_level"]
    slot_concept = slot["concept"]
    # For the user prompt, replace "inferred" with a natural-language fallback
    concept_display = slot_concept if slot_concept != "inferred" else "the main concept in this chunk"

    bloom_instr = BLOOM_INSTRUCTION.get(slot_bloom, BLOOM_INSTRUCTION["understand"])
    ct_instr = CHUNK_TYPE_FORM.get(
        chunk_type,
        "Use a general question style appropriate to the content.",
    )
    kw_str = ", ".join(keywords) if keywords else "(infer from text)"

    concept_block = _build_concept_block(slot, all_concepts)

    prev_s_disp = prev_s if prev_s else "N/A"
    next_s_disp = next_s if next_s else "N/A"

    parts = [
        "## CHUNK TEXT",
        text,
        "",
        "---",
        "",
        "## CONTEXT (background only -- do NOT write questions about these sentences)",
        f"Previous: {prev_s_disp}",
        f"Next    : {next_s_disp}",
        "",
        "---",
        "",
        "## METADATA",
        f"- chunk_type : {chunk_type}",
        f"- keywords   : {kw_str}",
        "",
        "---",
        "",
        "## YOUR TASK FOR THIS QUESTION",
        "Generate EXACTLY ONE MCQ. Not two. Not zero. One.",
        "Return a single JSON OBJECT (not an array).",
        "",
        concept_block,
        "",
        f"BLOOM LEVEL: {slot_bloom.upper()}",
        bloom_instr,
        "",
        "CHUNK TYPE INSTRUCTION",
        ct_instr,
        "",
        "FINAL REMINDER: You MUST output ONLY valid JSON format. Start your response with {",
    ]

    user_prompt = "\n".join(parts)

    return {
        "system_prompt": SFT_SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "slot_metadata": {
            "concept": slot_concept,
            "bloom_level": slot_bloom,
            "slot_type": slot.get("slot_type", "named"),
            "chunk_id": chunk.get("chunk_id", ""),
            "document_id": chunk.get("document_id", ""),
        },
    }


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def prepare_all_model_inputs(
    chunks: List[Dict],
    mcqs_per_chunk: int = 3,
) -> List[Dict]:
    """
    Transform enriched quiz chunks into model-ready input dicts.

    For each chunk:
      1. clean_concepts()  — validate / NLP fallback
      2. assign_slots()    — create 2–4 MCQ slots (capped by mcqs_per_chunk)
      3. build_model_input() — construct exact SFT-format prompt per slot

    Args:
        chunks: List of chunk dicts from the backend request. Each must have:
                  chunk_id, document_id, chunk_text, bloom_level, chunk_type,
                  concepts, keywords, context_prev_sentence, context_next_sentence
        mcqs_per_chunk: Max MCQs to generate per chunk (1–4). Default=3.

    Returns:
        Flat list of model-ready input dicts (one per slot).
        Each dict has: system_prompt, user_prompt, slot_metadata.
    """
    all_inputs: List[Dict] = []

    for chunk in chunks:
        # Step 1: Clean and validate concepts
        raw_concepts = chunk.get("concepts", [])
        chunk_text = chunk.get("chunk_text", "")
        concepts = clean_concepts(raw_concepts, chunk_text)

        # Step 2: Assign MCQ slots
        bloom_level = chunk.get("bloom_level", "understand")
        slots = assign_slots(concepts, bloom_level, max_slots=mcqs_per_chunk)

        # Step 3: Build model input for each slot
        for slot in slots:
            model_input = build_model_input(chunk, slot, concepts)
            all_inputs.append(model_input)

    return all_inputs
