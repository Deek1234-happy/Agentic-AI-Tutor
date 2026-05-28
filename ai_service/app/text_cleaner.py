# import re


# def clean_text(text: str) -> str:
#     text = remove_ocr_markers(text)
#     text = normalize_newlines(text)
#     text = normalize_spaces(text)
#     text = fix_common_ocr_errors(text)

#     return text.strip()


# # -------------------------
# # Cleaning helpers
# # -------------------------

# def remove_ocr_markers(text: str) -> str:
#     """
#     Removes developer/debug OCR markers.
#     """
#     return re.sub(r"\[OCR IMAGE TEXT\]", "", text)


# def normalize_newlines(text: str) -> str:
#     """
#     Reduces excessive newlines while keeping paragraph breaks.
#     """
#     # Replace Windows newlines
#     text = text.replace("\r\n", "\n")

#     # Collapse 3+ newlines into 2
#     text = re.sub(r"\n{3,}", "\n\n", text)

#     return text


# def normalize_spaces(text: str) -> str:
#     """
#     Normalizes spaces and tabs.
#     """
#     # Replace tabs with spaces
#     text = text.replace("\t", " ")

#     # Collapse multiple spaces
#     text = re.sub(r"[ ]{2,}", " ", text)

#     return text


# def fix_common_ocr_errors(text: str) -> str:
#     """
#     Fixes very common OCR artifacts without risking meaning.
#     """
#     replacements = {
#         "ﬁ": "fi",
#         "ﬂ": "fl",
#     }

#     for wrong, correct in replacements.items():
#         text = text.replace(wrong, correct)

#     return text

#############################################################

# app/text_cleaner.py
"""
Advanced text cleaning for the RAG pipeline.
Ported from quiz_engine.py TextCleaner — same logic, same quality gates.

Page / slide markers are NOT deleted — they are converted to a
special placeholder  __PGNUM_N__  that:
  • survives all cleaning filters (alpha ratio, length, garbage patterns)
  • lets chunker.py read page_start / page_end for each chunk
  • is stripped from the final chunk text by chunker.py

Public API (unchanged):
    from .text_cleaner import clean_text
    cleaned = clean_text(raw_text)
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import ftfy


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class CleaningConfig:
    remove_headers_footers: bool = True
    remove_page_numbers: bool = True
    normalize_unicode: bool = True
    fix_hyphenation: bool = True
    normalize_whitespace: bool = True
    remove_boilerplate: bool = True
    min_line_length: int = 20
    preserve_tables: bool = True
    language: str = "english"


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

LIGATURE_MAP = str.maketrans({
    "\uFB00": "ff", "\uFB01": "fi", "\uFB02": "fl",
    "\uFB03": "ffi", "\uFB04": "ffl",
    "\u2019": "'", "\u2018": "'",
    "\u201C": '"',  "\u201D": '"',
    "\u2013": "-",  "\u2014": "--",
    "\u00A0": " ",  "\u200B": "",  "\u00AD": "",
})

HEADING_RE = re.compile(
    r"""^(?:
        (?:Chapter|Section|Part|Unit|Module|Step|Lecture|Appendix)\s+[\dIVXivx]+
        | (?:\d+\.)+\s*[A-Z]
        | \d+\.\s+[A-Z][a-zA-Z]
    )""",
    re.VERBOSE | re.IGNORECASE,
)

MATH_LINE_RE = re.compile(
    r"""^[\s\d\+\-\*\/\=\(\)\[\]\{\}\^\_\.,;:σαβθ∑∫∂√∞≈≤≥±×÷<>|~%!?'"`@#&]+$"""
)

INLINE_MATH_RE = [
    re.compile(r"<<MATH_START>>.*?<<MATH_END>>", re.DOTALL),
    re.compile(r"\$[^\$]{1,80}\$"),
    re.compile(r"[A-Za-z]\s*[=<>]\s*[A-Za-z0-9\s\+\-\*\/\(\)]{1,40}(?=[,.\s]|$)"),
]

GARBAGE_PATTERNS = [
    re.compile(r"(.)\1{5,}"),
    re.compile(r"^[^a-zA-Z0-9\s]{4,}$"),
    re.compile(r"(?:aaa|eee|nnn|rrr){2,}", re.IGNORECASE),
    re.compile(r"(?:Siiee|BOPRNTETIEE|fentty|yaregtt|Pyeeneey|WNW\s+eae)", re.IGNORECASE),
    re.compile(r"(?:ieee\s+Oi|NE\s+ft|oii\s+Fe|NG\s+ae)", re.IGNORECASE),
    re.compile(r"(?:Asan\s*\||Wace\s*\||Tame\s+fa)", re.IGNORECASE),
    re.compile(r"(?:Hb\s+'|ett\s+Rare|NSM.*?Bosc)", re.IGNORECASE),
]

# Page-number placeholder produced by _remove_page_markers.
# Must be preserved through ALL line-filtering steps so chunker.py can
# read page_start / page_end from it.
_PGNUM_LINE_RE = re.compile(r"^__PGNUM_\d+__$")


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def is_heading(text: str) -> bool:
    t = text.strip()
    return bool(t) and len(t) <= 120 and bool(HEADING_RE.match(t))


# ═══════════════════════════════════════════════════════════════
# TEXT CLEANER CLASS
# ═══════════════════════════════════════════════════════════════

class TextCleaner:

    def __init__(self, config: Optional[CleaningConfig] = None):
        self.cfg = config or CleaningConfig()

    def clean(self, raw_text: str) -> str:
        text = raw_text
        text = self._normalize_unicode(text)
        text = self._fix_hyphenation(text)
        text = self._remove_page_markers(text)
        text = self._remove_boilerplate(text)
        text = self._remove_headers_footers(text)
        text = self._clean_lines(text)
        text = self._strip_inline_math(text)
        text = self._normalize_bullets(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    def _normalize_unicode(self, text: str) -> str:
        text = ftfy.fix_text(text)
        return unicodedata.normalize("NFC", text).translate(LIGATURE_MAP)

    def _fix_hyphenation(self, text: str) -> str:
        return re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    def _remove_page_markers(self, text: str) -> str:
        # Convert page / slide markers to a placeholder that survives all
        # cleaning filters.  chunker.py reads the page numbers back from
        # these placeholders and then strips them from the chunk text.
        def _page_sub(m: re.Match) -> str:
            return f"__PGNUM_{m.group(2)}__"

        text = re.sub(
            r"---\s*(Page|Slide)\s+(\d+)\s*---",
            _page_sub,
            text,
            flags=re.IGNORECASE,
        )
        # Strip bare standalone page-number lines (e.g. "  5  " alone)
        text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)
        return text

    def _remove_boilerplate(self, text: str) -> str:
        for pattern in [
            r"ISBN[:\s-]*[\d\-X]{10,17}",
            r"©\s*\d{4}.*",
            r"Copyright\s+©?\s*\d{4}.*",
            r"All rights reserved\.?",
            r"https?://\S+",
            r"Image taken from.*",
            r"Figure\s+\d+[\.:].{0,120}",
        ]:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text

    def _remove_headers_footers(self, text: str) -> str:
        lines = text.split("\n")
        freq = Counter(l.strip().lower() for l in lines if l.strip())
        repeated = {l for l, c in freq.items() if c >= 3 and len(l) < 100}
        return "\n".join(
            l for l in lines
            if l.strip().lower() not in repeated or len(l.strip()) >= 100
        )

    def _clean_lines(self, text: str) -> str:
        lines = text.split("\n")
        result = []
        for line in lines:
            s = line.strip()
            if not s:
                result.append("")
                continue
            # ── Always preserve page-number placeholders ──────────────────────
            # __PGNUM_N__ is short (< min_line_length) but must not be
            # dropped — chunker.py reads page numbers from these markers.
            if _PGNUM_LINE_RE.match(s):
                result.append(line)
                continue
            if is_heading(s):
                result.append(line)
                continue
            if any(p.search(s) for p in GARBAGE_PATTERNS):
                continue
            if MATH_LINE_RE.match(s) and len(s) > 5:
                continue
            non_space = s.replace(" ", "")
            if non_space:
                alpha_r = sum(c.isalpha() for c in non_space) / len(non_space)
                if alpha_r < 0.45 and len(s) > 12:
                    continue
            tokens = s.split()
            if len(tokens) >= 5:
                short = sum(1 for t in tokens if len(re.sub(r"[^a-zA-Z]", "", t)) <= 2)
                if short / len(tokens) > 0.60:
                    continue
            if s.count("|") >= 2 and len(s) < 80:
                s = s.replace("|", ", ")
            if len(s) < self.cfg.min_line_length and not is_heading(s):
                continue
            result.append(line)
        return "\n".join(result)

    def _strip_inline_math(self, text: str) -> str:
        for pattern in INLINE_MATH_RE:
            text = pattern.sub(" ", text)
        return re.sub(r"\s{2,}", " ", text)

    def _normalize_bullets(self, text: str) -> str:
        text = re.sub(r"^[¢°•·▪▸◦‣⁃]\s*", "• ", text, flags=re.MULTILINE)
        text = re.sub(r"^o\s+(?=[A-Z])", "• ", text, flags=re.MULTILINE)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

_cleaner_singleton: Optional[TextCleaner] = None


def clean_text(text: str) -> str:
    """
    Public API — clean raw extracted text.
    Drop-in replacement for the old clean_text(); same signature.
    Uses full TextCleaner: unicode fix, garbage-line filtering,
    boilerplate removal, header/footer dedup, inline-math stripping.
    """
    global _cleaner_singleton
    if _cleaner_singleton is None:
        _cleaner_singleton = TextCleaner()
    return _cleaner_singleton.clean(text)