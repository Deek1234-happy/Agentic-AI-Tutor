import re


def clean_text(text: str) -> str:
    text = remove_ocr_markers(text)
    text = normalize_newlines(text)
    text = normalize_spaces(text)
    text = fix_common_ocr_errors(text)

    return text.strip()


# -------------------------
# Cleaning helpers
# -------------------------

def remove_ocr_markers(text: str) -> str:
    """
    Removes developer/debug OCR markers.
    """
    return re.sub(r"\[OCR IMAGE TEXT\]", "", text)


def normalize_newlines(text: str) -> str:
    """
    Reduces excessive newlines while keeping paragraph breaks.
    """
    # Replace Windows newlines
    text = text.replace("\r\n", "\n")

    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def normalize_spaces(text: str) -> str:
    """
    Normalizes spaces and tabs.
    """
    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces
    text = re.sub(r"[ ]{2,}", " ", text)

    return text


def fix_common_ocr_errors(text: str) -> str:
    """
    Fixes very common OCR artifacts without risking meaning.
    """
    replacements = {
        "ﬁ": "fi",
        "ﬂ": "fl",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    return text