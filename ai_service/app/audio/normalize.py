import re
from typing import Optional


# -----------------------------
# RULE-BASED CLEANING
# -----------------------------

FILLER_PATTERNS = [
    r"\bumm+\b",
    r"\buh+\b",
    r"\blike\b",
    r"\byou know\b",
    r"\bi mean\b",
    r"\bkind of\b",
    r"\bsort of\b"
]


def remove_fillers(text: str) -> str:
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def remove_repeated_words(text: str) -> str:
    return re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)


def clean_spacing(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def add_basic_punctuation(text: str) -> str:
    if not text:
        return text

    if not text.endswith((".", "?", "!")):
        if text.lower().startswith(("what", "why", "how", "can", "does", "is", "are", "do")):
            text += "?"
        else:
            text += "."
    return text


def capitalize_text(text: str) -> str:
    if text:
        text = text[0].upper() + text[1:]
    return text


def rule_based_normalize(text: str) -> str:
    text = remove_fillers(text)
    text = remove_repeated_words(text)
    text = clean_spacing(text)
    text = capitalize_text(text)
    text = add_basic_punctuation(text)
    return text


# -----------------------------
# LLM CLEANUP (OPTIONAL)
# -----------------------------

def llm_cleanup(text: str, llm_callable) -> str:
    """
    llm_callable should be your LLM generate function.
    """

    prompt = f"""
You are cleaning a speech-to-text transcript.

Rewrite it into a clear, grammatically correct sentence.
Do NOT change the meaning.
Do NOT add new information.

Transcript:
{text}

Clean version:
"""

    cleaned = llm_callable(prompt)
    return cleaned.strip()


# -----------------------------
# HYBRID NORMALIZATION
# -----------------------------

def normalize_text(
    text: str,
    stt_confidence: float,
    llm_callable: Optional[callable] = None,
    confidence_threshold: float = 0.75
) -> str:
    """
    Hybrid normalization:
    - Always apply rule-based cleaning
    - If STT confidence is high and LLM provided, apply LLM cleanup
    """

    if not text:
        return ""

    # Step 1: rule-based
    cleaned_text = rule_based_normalize(text)

    # Step 2: optional LLM refinement
    if llm_callable and stt_confidence >= confidence_threshold:
        try:
            cleaned_text = llm_cleanup(cleaned_text, llm_callable)
        except Exception:
            pass  # fallback to rule-based only

    return cleaned_text