LANGUAGES = {
    "en": {"name": "English", "locale": "en-IN", "whisper": "en", "idk": "I don't know."},
    "kn": {"name": "Kannada", "locale": "kn-IN", "whisper": "kn", "idk": "ನನಗೆ ತಿಳಿದಿಲ್ಲ."},
    "hi": {"name": "Hindi", "locale": "hi-IN", "whisper": "hi", "idk": "मुझे नहीं पता।"},
    "ml": {"name": "Malayalam", "locale": "ml-IN", "whisper": "ml", "idk": "എനിക്കറിയില്ല."},
    "ta": {"name": "Tamil", "locale": "ta-IN", "whisper": "ta", "idk": "எனக்குத் தெரியாது."},
    "te": {"name": "Telugu", "locale": "te-IN", "whisper": "te", "idk": "నాకు తెలియదు."},
}


def normalize_language(language):
    code = str(language or "en").strip().lower()
    if code not in LANGUAGES:
        raise ValueError("Unsupported language. Choose en, kn, hi, ml, ta, or te.")
    return code


def response_language_instruction(language):
    code = normalize_language(language)
    if code == "en":
        return ""

    name = LANGUAGES[code]["name"]
    return (
        f"Write the final response in {name}. Keep technical terms, code blocks, "
        "filenames, URLs, and citation/source identifiers unchanged. Explain "
        "around code without translating code or altering source references."
    )


def idk_message(language):
    return LANGUAGES[normalize_language(language)]["idk"]