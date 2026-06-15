# app/quiz/quiz_cleaner.py
"""
Quiz-specific text cleaner.

Identical cleaning logic to app/text_cleaner.py with ONE key difference:

  RAG cleaner  → converts page/slide markers to __PGNUM_N__ placeholders
                  so chunker.py can extract page_start / page_end ranges.

  Quiz cleaner → strips ALL page/slide markers completely.
                  Quiz chunks do NOT need page ranges, so there is no reason
                  to preserve __PGNUM_N__ tokens through the pipeline.

Public API:
    from .quiz_cleaner import clean_text_for_quiz
    cleaned = clean_text_for_quiz(raw_text)
"""

import re
import unicodedata
from collections import Counter
from typing import Optional

import ftfy

from .quiz_config import QuizCleaningConfig


# ═══════════════════════════════════════════════════════════════
# CONSTANTS  (identical to text_cleaner.py)
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

# Matches any __PGNUM_N__ token that may have survived parsing / other cleaners.
_PGNUM_ANY_RE = re.compile(r"__PGNUM_\d+__")


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _is_heading(text: str) -> bool:
    t = text.strip()
    return bool(t) and len(t) <= 120 and bool(HEADING_RE.match(t))


# ═══════════════════════════════════════════════════════════════
# QUIZ TEXT CLEANER
# ═══════════════════════════════════════════════════════════════

class QuizTextCleaner:
    """
    Cleans raw extracted text for the quiz chunking pipeline.

    Differs from RAG TextCleaner in _remove_page_markers():
      • Page/slide markers are DELETED outright.
      • __PGNUM_N__ placeholders (if already present) are also stripped.
      • No placeholder is introduced — quiz chunker doesn't need page ranges.
    """

    def __init__(self, config: Optional[QuizCleaningConfig] = None):
        self.cfg = config or QuizCleaningConfig()

    def clean(self, raw_text: str) -> str:
        text = raw_text
        text = self._normalize_unicode(text)
        text = self._fix_hyphenation(text)
        text = self._remove_page_markers(text)   # ← quiz-specific behaviour
        text = self._remove_boilerplate(text)
        text = self._remove_headers_footers(text)
        text = self._clean_lines(text)
        text = self._strip_inline_math(text)
        text = self._normalize_bullets(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    # ── private methods ───────────────────────────────────────────────────────

    def _normalize_unicode(self, text: str) -> str:
        text = ftfy.fix_text(text)
        return unicodedata.normalize("NFC", text).translate(LIGATURE_MAP)

    def _fix_hyphenation(self, text: str) -> str:
        return re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    def _remove_page_markers(self, text: str) -> str:
        """
        Quiz version: completely remove page/slide markers.

        Unlike the RAG cleaner which converts them to __PGNUM_N__ sentinels,
        we delete them entirely because quiz chunks do not use page ranges.

        Three cases handled:
          1.  --- Page 5 ---   or   --- Slide 5 ---   (parser output)
          2.  __PGNUM_5__      (already converted by a prior pass / RAG path)
          3.  Bare standalone digit lines  ("  5  " alone on a line)
        """
        # 1. Raw markers from parsers
        text = re.sub(r"---\s*(Page|Slide)\s+\d+\s*---", "", text, flags=re.IGNORECASE)
        # 2. Already-converted __PGNUM_N__ tokens (defensive)
        text = _PGNUM_ANY_RE.sub("", text)
        # 3. Bare standalone page-number lines
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
            if _is_heading(s):
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
            if len(s) < self.cfg.min_line_length and not _is_heading(s):
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

_quiz_cleaner_singleton: Optional[QuizTextCleaner] = None


def clean_text_for_quiz(text: str) -> str:
    """
    Public API — clean raw extracted text for the quiz pipeline.

    Strips __PGNUM_N__ markers completely (unlike RAG's clean_text which
    preserves them as page-range sentinels).

    Usage:
        from .quiz_cleaner import clean_text_for_quiz
        cleaned = clean_text_for_quiz(raw_text)
    """
    global _quiz_cleaner_singleton
    if _quiz_cleaner_singleton is None:
        _quiz_cleaner_singleton = QuizTextCleaner()
    return _quiz_cleaner_singleton.clean(text)
