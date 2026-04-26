# app/quiz_engine.py
"""
Complete semantic chunking engine — all internal logic in one file.

Sections:
  A. TextCleaner         — cleans raw extracted text
  B. SemanticChunker     — splits text into semantic chunks
  C. ChunkValidator      — scores chunk quality
  D. chunk_text()        — main adapter (cleaner + chunker + validator)
  E. postprocess()       — dedup + micro-header injection

Usage in processor.py:
    from .quiz_engine import TextCleaner, chunk_text, postprocess
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import numpy as np
import ftfy

from .quiz_config import ChunkingConfig, CleaningConfig


# ═══════════════════════════════════════════════════════════════════════════════
# A. TEXT CLEANER
# ═══════════════════════════════════════════════════════════════════════════════

LIGATURE_MAP = str.maketrans({
    "\uFB00": "ff", "\uFB01": "fi", "\uFB02": "fl",
    "\uFB03": "ffi", "\uFB04": "ffl",
    "\u2019": "'", "\u2018": "'",
    "\u201C": '"', "\u201D": '"',
    "\u2013": "-", "\u2014": "--",
    "\u00A0": " ", "\u200B": "", "\u00AD": "",
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


def is_heading(text: str) -> bool:
    t = text.strip()
    return bool(t) and len(t) <= 120 and bool(HEADING_RE.match(t))


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

    def _normalize_unicode(self, text):
        text = ftfy.fix_text(text)
        return unicodedata.normalize("NFC", text).translate(LIGATURE_MAP)

    def _fix_hyphenation(self, text):
        return re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    def _remove_page_markers(self, text):
        text = re.sub(r"---\s*Page\s+\d+\s*---", "", text, flags=re.IGNORECASE)
        text = re.sub(r"---\s*Slide\s+\d+\s*---", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)
        return text

    def _remove_boilerplate(self, text):
        for p in [
            r"ISBN[:\s-]*[\d\-X]{10,17}", r"©\s*\d{4}.*",
            r"Copyright\s+©?\s*\d{4}.*", r"All rights reserved\.?",
            r"https?://\S+", r"Image taken from.*",
            r"Figure\s+\d+[\.:].{0,120}",
        ]:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        return text

    def _remove_headers_footers(self, text):
        lines = text.split("\n")
        freq = Counter(l.strip().lower() for l in lines if l.strip())
        repeated = {l for l, c in freq.items() if c >= 3 and len(l) < 100}
        return "\n".join(
            l for l in lines
            if l.strip().lower() not in repeated or len(l.strip()) >= 100
        )

    def _clean_lines(self, text):
        lines = text.split("\n")
        result = []
        for line in lines:
            s = line.strip()
            if not s:
                result.append("")
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
                continue
                # s = s.replace("|", ", ")
            if len(s) < self.cfg.min_line_length and not is_heading(s):
                continue
            result.append(line)
        return "\n".join(result)

    def _strip_inline_math(self, text):
        for pattern in INLINE_MATH_RE:
            text = pattern.sub(" ", text)
        return re.sub(r"\s{2,}", " ", text)

    def _normalize_bullets(self, text):
        text = re.sub(r"^[¢°•·▪▸◦‣⁃]\s*", "• ", text, flags=re.MULTILINE)
        text = re.sub(r"^o\s+(?=[A-Z])", "• ", text, flags=re.MULTILINE)
        return text

    def _normalize_whitespace(self, text):
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED EMBEDDING SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_shared_embedder = None


def _get_embedder(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    global _shared_embedder
    if _shared_embedder is None:
        from sentence_transformers import SentenceTransformer
        _shared_embedder = SentenceTransformer(model_name)
    return _shared_embedder


# ═══════════════════════════════════════════════════════════════════════════════
# B. SEMANTIC CHUNKER
# ═══════════════════════════════════════════════════════════════════════════════

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _chunk_id(text: str, idx: int) -> str:
    return hashlib.sha1(f"{idx}-{text[:60]}".encode()).hexdigest()[:10]


def _window_avg(embs: np.ndarray, idx: int, w: int) -> np.ndarray:
    half = w // 2
    return embs[max(0, idx - half): min(len(embs), idx + half + 1)].mean(axis=0)


@dataclass
class Chunk:
    chunk_id: str
    index: int
    text: str
    sentences: List[str]
    token_count: int
    char_count: int
    start_sentence_idx: int
    end_sentence_idx: int
    heading: Optional[str] = None
    is_table: bool = False
    semantic_score: float = 0.0
    # ── context fringe ────────────────────────────────────────────────────────
    # The single sentence immediately before / after this chunk's boundary.
    # Passed to LLM prompts in S3 and S4 for boundary context.
    # NOT part of chunk.text — does not affect scoring, dedup, or size filters.
    prev_sentence: Optional[str] = None
    next_sentence: Optional[str] = None
    # ─────────────────────────────────────────────────────────────────────────
    metadata: dict = field(default_factory=dict)


class SemanticChunker:

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.cfg = config or ChunkingConfig()

    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        metadata = metadata or {}
        sentences, heading_flags = self._split(text)
        if not sentences:
            return []
        embeddings = self._embed(sentences)
        similarities = self._similarities(embeddings)
        breakpoints = self._breakpoints(similarities, heading_flags)
        raw = self._build_raw(sentences, breakpoints)
        sized = self._size_constrain(raw, embeddings)
        overlapped = self._add_overlap(sized)
        chunks = self._finalise(overlapped, embeddings, metadata)
        chunks = self._attach_fringe(chunks)
        return chunks

    def _split(self, text: str) -> Tuple[List[str], List[bool]]:
        sentences, flags = [], []
        for para in re.split(r"\n\n+", text):
            para = para.strip()
            if not para:
                continue
            if is_heading(para) and len(para.split()) <= 12:
                sentences.append(para)
                flags.append(True)
                continue
            for s in self._regex_split(para):
                s = s.strip()
                if len(s) < self.cfg.min_sentence_length:
                    continue
                sentences.append(s)
                flags.append(False)
        return sentences, flags

    @staticmethod
    def _regex_split(text: str) -> List[str]:
        text = re.sub(
            r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e|Fig|Eq|No|pp)\.",
            r"\1<DOT>", text, flags=re.IGNORECASE
        )
        text = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", text)
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\(•])", text)
        return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]

    def _embed(self, sentences: List[str]) -> np.ndarray:
        # Uses the shared singleton — no duplicate model loading
        model = _get_embedder(self.cfg.embedding_model)
        return model.encode(sentences, batch_size=64,
                            show_progress_bar=len(sentences) > 100,
                            normalize_embeddings=True)

    def _similarities(self, embs: np.ndarray) -> List[float]:
        w = self.cfg.window_size
        return [_cosine(_window_avg(embs, i, w), _window_avg(embs, i + 1, w))
                for i in range(len(embs) - 1)]

    def _breakpoints(self, sims: List[float], heading_flags: List[bool]) -> List[int]:
        if not sims:
            return [0]
        arr = np.array(sims)
        if self.cfg.dynamic_similarity:
            threshold = np.mean(arr) - (np.std(arr) * self.cfg.similarity_std_factor)
        else:
            threshold = np.percentile(arr, 100 - self.cfg.breakpoint_percentile)
        drop_breaks = {i + 1 for i, s in enumerate(sims)
                       if s < threshold or s < self.cfg.similarity_threshold}
        heading_breaks = {i for i, h in enumerate(heading_flags) if h}
        return sorted({0} | drop_breaks | heading_breaks)

    def _build_raw(self, sentences: List[str], breakpoints: List[int]) -> List[dict]:
        chunks = []
        for j, start in enumerate(breakpoints):
            end = breakpoints[j + 1] if j + 1 < len(breakpoints) else len(sentences)
            sents = sentences[start:end]
            if len(sents) > self.cfg.max_sentences_per_chunk:
                for i in range(0, len(sents), self.cfg.max_sentences_per_chunk):
                    sub = sents[i:i + self.cfg.max_sentences_per_chunk]
                    chunks.append({"sentences": sub, "start": start + i,
                                   "end": start + i + len(sub) - 1})
                continue
            if sents:
                chunks.append({"sentences": sents, "start": start, "end": end - 1})
        return chunks

    def _size_constrain(self, chunks: List[dict], embs: np.ndarray) -> List[dict]:
        split = []
        for c in chunks:
            if _tokens(" ".join(c["sentences"])) > self.cfg.max_chunk_tokens:
                split.extend(self._split_chunk(c, embs))
            else:
                split.append(c)
        if not self.cfg.merge_orphans or len(split) < 2:
            return split
        merged, i = [], 0
        while i < len(split):
            c = split[i]
            if _tokens(" ".join(c["sentences"])) < self.cfg.min_chunk_tokens:
                if merged:
                    merged[-1]["sentences"].extend(c["sentences"])
                    merged[-1]["end"] = c["end"]
                elif i + 1 < len(split):
                    split[i + 1]["sentences"] = c["sentences"] + split[i + 1]["sentences"]
                    split[i + 1]["start"] = c["start"]
                    i += 1
                    merged.append(split[i])
                    i += 1
                    continue
                else:
                    merged.append(c)
            else:
                merged.append(c)
            i += 1
        return merged

    def _split_chunk(self, chunk: dict, embs: np.ndarray) -> List[dict]:
        sents, start = chunk["sentences"], chunk["start"]
        if len(sents) <= 1:
            return [chunk]
        sub_embs = embs[start: start + len(sents)]
        if len(sub_embs) < 2:
            return [chunk]
        sims = [_cosine(sub_embs[i], sub_embs[i + 1]) for i in range(len(sub_embs) - 1)]
        split_at = int(np.argmin(sims)) + 1
        left = {"sentences": sents[:split_at], "start": start, "end": start + split_at - 1}
        right = {"sentences": sents[split_at:], "start": start + split_at, "end": chunk["end"]}
        result = []
        for part in (left, right):
            if _tokens(" ".join(part["sentences"])) > self.cfg.max_chunk_tokens:
                result.extend(self._split_chunk(part, embs))
            else:
                result.append(part)
        return result

    def _add_overlap(self, chunks: List[dict]) -> List[dict]:
        n = self.cfg.overlap_sentences
        if n == 0 or len(chunks) < 2:
            return chunks
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]["sentences"]
            overlap = prev[-n:] if len(prev) >= n else prev
            new = dict(chunks[i])
            new["sentences"] = overlap + new["sentences"]
            result.append(new)
        return result

    def _finalise(self, chunks: List[dict], embs: np.ndarray, metadata: dict) -> List[Chunk]:
        final, current_heading = [], None
        for i, c in enumerate(chunks):
            sents = c["sentences"]
            text = " ".join(sents).strip()
            if not text:
                continue
            for s in sents:
                if is_heading(s.strip()):
                    current_heading = s.strip()
            sub = embs[c["start"]: c["end"] + 1]
            score = float(np.mean([_cosine(sub[j], sub[j + 1])
                                   for j in range(len(sub) - 1)])) if len(sub) >= 2 else 1.0
            final.append(Chunk(
                chunk_id=_chunk_id(text, i), index=i, text=text, sentences=sents,
                token_count=_tokens(text), char_count=len(text),
                start_sentence_idx=c["start"], end_sentence_idx=c["end"],
                heading=current_heading, is_table=False,
                semantic_score=round(score, 4),
                metadata={**metadata, "chunk_index": i},
            ))
        return final

    # ── context fringe ────────────────────────────────────────────────────────

    @staticmethod
    def _first_real_sentence(sentences: List[str]) -> Optional[str]:
        """
        Return the first sentence from a list that is a real sentence
        (not a bullet-list block containing newlines).
        Falls back to the first entry if nothing qualifies.
        """
        for s in sentences:
            # Take first line only — guards against multi-line bullet blocks
            first_line = s.split("\n")[0].strip()
            if first_line and len(first_line.split()) >= 3:
                return first_line
        # fallback: first non-empty entry, first line only
        for s in sentences:
            first_line = s.split("\n")[0].strip()
            if first_line:
                return first_line
        return None

    @staticmethod
    def _last_real_sentence(sentences: List[str]) -> Optional[str]:
        """
        Return the last real sentence (last line of the last entry).
        Same multi-line guard as _first_real_sentence.
        """
        for s in reversed(sentences):
            last_line = s.split("\n")[-1].strip()
            if last_line and len(last_line.split()) >= 3:
                return last_line
        for s in reversed(sentences):
            last_line = s.split("\n")[-1].strip()
            if last_line:
                return last_line
        return None

    @classmethod
    def _attach_fringe(cls, chunks: List[Chunk]) -> List[Chunk]:
        """
        Attach context fringe to each chunk:
          prev_sentence — last sentence of the preceding chunk (clean, single line)
          next_sentence — first sentence of the following chunk (clean, single line)

        First chunk → prev_sentence = None
        Last chunk  → next_sentence = None
        """
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk.prev_sentence = cls._last_real_sentence(chunks[i - 1].sentences)
            else:
                chunk.prev_sentence = None

            if i < len(chunks) - 1:
                chunk.next_sentence = cls._first_real_sentence(chunks[i + 1].sentences)
            else:
                chunk.next_sentence = None

        return chunks

    # ─────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
# C. CHUNK VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    chunk_id: str
    index: int
    passed: bool
    score: float
    issues: List[str]
    scores: dict


class ChunkValidator:

    def __init__(self, config: ChunkingConfig = None):
        self.cfg = config or ChunkingConfig()

    def validate(self, chunk: Chunk) -> ValidationResult:
        issues, scores = [], {}
        scores["semantic"] = self._score_semantic(chunk, issues)
        scores["size"] = self._score_size(chunk, issues)
        scores["text_quality"] = self._score_text_quality(chunk, issues)
        scores["completeness"] = self._score_completeness(chunk, issues)
        scores["sentence_count"] = self._score_sentence_count(chunk, issues)
        weights = {"semantic": 0.30, "size": 0.20, "text_quality": 0.25,
                   "completeness": 0.15, "sentence_count": 0.10}
        composite = sum(scores[k] * weights[k] for k in weights)
        passed = composite >= self.cfg.quality_score_threshold and len(issues) == 0
        return ValidationResult(chunk_id=chunk.chunk_id, index=chunk.index,
                                passed=passed, score=round(composite, 4),
                                issues=issues,
                                scores={k: round(v, 4) for k, v in scores.items()})

    def validate_all(self, chunks: List[Chunk]) -> List[ValidationResult]:
        return [self.validate(c) for c in chunks]

    def _score_semantic(self, chunk, issues):
        score = float(chunk.semantic_score or 0.0)
        if score < 0.40:
            issues.append(f"Low semantic coherence ({score:.2f})")
        return max(0.0, min(1.0, score))

    def _score_size(self, chunk, issues):
        t = chunk.token_count or 0
        if t == 0:
            issues.append("Empty chunk")
            return 0.0
        if t < self.cfg.min_chunk_tokens:
            issues.append(f"Too short ({t} tokens)")
            return 0.0
        if t > self.cfg.max_chunk_tokens:
            issues.append(f"Too long ({t} tokens)")
            return 0.2
        return max(0.0, 1.0 - abs(t - self.cfg.target_chunk_tokens) / max(self.cfg.target_chunk_tokens, 1))

    def _score_text_quality(self, chunk, issues):
        text = chunk.text or ""
        if not text:
            issues.append("Empty text")
            return 0.0
        score = 1.0
        length = max(len(text), 1)
        if sum(1 for c in text if ord(c) > 127) / length > 0.18:
            issues.append("High OCR noise")
            score -= 0.35
        if len(re.findall(r"[^\w\s]", text)) / length > 0.22:
            issues.append("High symbol ratio")
            score -= 0.25
        if sum(c.isdigit() for c in text) / length > 0.40 and not chunk.is_table:
            issues.append("High digit ratio")
            score -= 0.2
        if re.search(r"(.)\1{6,}", text):
            issues.append("Repeated character noise")
            score -= 0.3
        if len(text.split()) < 8:
            issues.append("Very low word count")
            score -= 0.25
        return max(0.0, score)

    def _score_completeness(self, chunk, issues):
        text = (chunk.text or "").strip()
        if not text:
            return 0.0
        score = 1.0
        if chunk.index > 0 and text[0].islower():
            issues.append("Possible truncated start")
            score -= 0.25
        if text[-1] not in ".!?\"'»)]":
            issues.append("Missing terminal punctuation")
            score -= 0.2
        if re.search(r"\w-$", text):
            issues.append("Broken hyphenated word")
            score -= 0.2
        return max(0.0, score)

    def _score_sentence_count(self, chunk, issues):
        n = len(chunk.sentences)
        if n == 0:
            return 0.0
        if n < 2:
            issues.append("Too few sentences")
            return 0.4
        if n > 25:
            issues.append("Too many sentences")
            return 0.65
        return 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# D. CHUNK_TEXT — main adapter
# ═══════════════════════════════════════════════════════════════════════════════

_chunker_singleton = None
_validator_singleton = None


def _init_engine():
    global _chunker_singleton, _validator_singleton
    if _chunker_singleton is None:
        cfg = ChunkingConfig()
        _chunker_singleton = SemanticChunker(cfg)
        _validator_singleton = ChunkValidator(cfg)
    return _chunker_singleton, _validator_singleton


_NOISE_RE = re.compile(
    r"""
    (?:aaa|eee|nnn|rrr){2,}
    | (?:Siiee|BOPRNTETIEE|fentty|yaregtt|Pyeeneey)
    | (?:Asan\s*\||Wace\s*\||Tame\s+fa|NE\s+ft)
    | ^[^a-zA-Z]{6,}$
    | ^[=\-\+\*\.]{3,}
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _is_noise(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return True
    if _NOISE_RE.search(s):
        return True
    non_space = s.replace(" ", "")
    if non_space and sum(c.isalpha() for c in non_space) / len(non_space) < 0.40:
        return True
    tokens = s.split()
    if len(tokens) >= 5:
        short = sum(1 for t in tokens if len(re.sub(r"[^a-zA-Z]", "", t)) <= 2)
        if short / len(tokens) > 0.65:
            return True
    return False


def _clean_heading(heading: Optional[str]) -> str:
    if not heading:
        return "General Content"
    line = heading.split("\n")[0].strip()
    if len(line) > 100 or len(line.split()) > 12:
        return "General Content"
    if len(re.findall(r"[a-zA-Z]{3,}", line)) < 2:
        return "General Content"
    if sum(c.isalpha() for c in line) / max(len(line), 1) < 0.50:
        return "General Content"
    return line


def chunk_text(text: str, file_id: str, source_type: str = None) -> List[Dict]:
    """
    Main entry: clean text → list of chunk dicts ready for postprocess().
    All config values come from quiz_config.py → ChunkingConfig.

    Each output dict includes:
      context_fringe: {
        prev_sentence: str | None,  — last sentence of the preceding chunk
        next_sentence: str | None   — first sentence of the following chunk
      }
    The fringe is NOT part of 'text'. Pass it separately to S3/S4 LLM prompts.
    """
    chunker, validator = _init_engine()
    cfg = chunker.cfg
    min_words = max(35, int(cfg.min_chunk_tokens * 0.6))

    print(f"[Chunking] START {file_id} | building candidate chunks", flush=True)
    chunks = chunker.chunk(text, metadata={"file_id": file_id})
    results = validator.validate_all(chunks)

    output = []
    skipped_empty = 0
    skipped_short_or_low_quality = 0
    skipped_low_semantic = 0
    for chunk, result in zip(chunks, results):
        clean_sents = [s for s in chunk.sentences
                       if not _is_noise(s) and len(s.split()) >= 5]
        if not clean_sents:
            skipped_empty += 1
            continue
        clean_text = " ".join(s.strip() for s in clean_sents)
        word_count = len(clean_text.split())
        if word_count < min_words or result.score < cfg.quality_score_threshold:
            skipped_short_or_low_quality += 1
            continue

        if chunk.semantic_score < cfg.min_semantic_score:
            skipped_low_semantic += 1
            continue

        context_fringe = {
            "prev_sentence": chunk.prev_sentence,
            "next_sentence": chunk.next_sentence,
        }

        output.append({
            "file_id":         file_id,
            "chunk_id":        f"{file_id}_{len(output) + 1}",
            "concept_heading": _clean_heading(chunk.heading),
            "text":            clean_text,
            "context_fringe":  context_fringe,
            "word_count":      word_count,
            "token_count":     chunk.token_count,
            "semantic_score":  round(chunk.semantic_score, 4),
            "quality_score":   round(result.score, 4),
        })
    print(
        f"[Chunking] DONE  {file_id} | candidates={len(chunks)} kept={len(output)} "
        f"skipped_empty={skipped_empty} skipped_low_quality={skipped_short_or_low_quality} "
        f"skipped_low_semantic={skipped_low_semantic}",
        flush=True,
    )
    return output


# ═══════════════════════════════════════════════════════════════════════════════
# E. POSTPROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════
_summarizer = None


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        try:
            from transformers import pipeline
            _summarizer = pipeline("summarization", model="facebook/bart-large-cnn",
                                   device=-1, truncation=True)
            print("[PostProcessor] BART summarizer loaded.")
        except Exception as e:
            print(f"[PostProcessor] BART not available ({e}). Using extractive fallback.")
            _summarizer = "fallback"
    return _summarizer


def _cosine_post(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def remove_intra_repetition(chunks: List[Dict]) -> List[Dict]:
    result = []
    for chunk in chunks:
        text = chunk.get("text", "")
        raw_sents = re.split(r"(?<=[.!?])\s+", text)
        seen, unique_sents = set(), []
        for s in raw_sents:
            key = re.sub(r"\s+", " ", s.strip().lower())
            if len(key) < 10:
                unique_sents.append(s)
                continue
            if key not in seen:
                seen.add(key)
                unique_sents.append(s)
        new_text = " ".join(unique_sents).strip()
        if new_text != text:
            chunk = dict(chunk)
            chunk["text"] = new_text
            chunk["word_count"] = len(new_text.split())
        result.append(chunk)
    return result


def filter_by_size(chunks: List[Dict], min_words: int = 50, max_words: int = 350) -> List[Dict]:
    result = []
    for chunk in chunks:
        wc = chunk.get("word_count", len(chunk.get("text", "").split()))
        if wc < min_words or wc > max_words:
            continue
        chunk = dict(chunk)
        chunk["word_count"] = wc
        result.append(chunk)
    return result


def deduplicate_chunks(chunks: List[Dict], similarity_threshold: float = 0.92) -> List[Dict]:
    if len(chunks) <= 1:
        return chunks
    # Uses the shared singleton — same model, no second load
    model = _get_embedder()
    embeddings = model.encode([c["text"] for c in chunks],
                              normalize_embeddings=True, batch_size=64)
    kept, kept_embs = [], []
    for i, emb in enumerate(embeddings):
        if not any(_cosine_post(emb, k) > similarity_threshold for k in kept_embs):
            kept.append(chunks[i])
            kept_embs.append(emb)
    removed = len(chunks) - len(kept)
    if removed > 0:
        print(f"[Dedup] Removed {removed} duplicate chunk(s)")
    file_id = chunks[0].get("file_id", "doc") if chunks else "doc"
    for idx, c in enumerate(kept):
        c["chunk_id"] = f"{file_id}_{idx + 1}"
    return kept


_GENERIC_HEADINGS = {"general content", "step 1: keypoint computations?",
                     "step 1: keypoint computations", "keypoint computations"}


def _is_generic_heading(heading: str) -> bool:
    return not heading or heading.strip().lower() in _GENERIC_HEADINGS


def _generate_header_bart(text: str, summarizer) -> str:
    try:
        result = summarizer(text[:800], max_length=20, min_length=5,
                            do_sample=False, num_beams=4)
        header = result[0]["summary_text"].strip().split(".")[0].strip()
        words = header.split()
        if len(words) > 15:
            header = " ".join(words[:15])
        return header if len(header) > 10 else _generate_header_extractive(text)
    except Exception:
        return _generate_header_extractive(text)


def _generate_header_extractive(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
    if not lines:
        return "General Content"
    candidates = []
    for line in lines[:5]:
        clean = re.sub(r"^[•\-\*o\d\.]+\s*", "", line).strip()
        if len(clean.split()) >= 4:
            candidates.append(clean)
    best = candidates[0] if candidates else lines[0]
    return " ".join(best.split()[:12]).rstrip(",:;") or "General Content"


def inject_micro_headers(chunks: List[Dict], document_title: Optional[str] = None,
                         use_bart: bool = False) -> List[Dict]:
    summarizer = _get_summarizer() if use_bart else "fallback"
    enriched = []
    for chunk in chunks:
        chunk = dict(chunk)
        text = chunk["text"]
        title = document_title or chunk.get("file_id", "document").replace("_", " ").replace("-", " ").title()
        existing = chunk.get("concept_heading", "")
        micro_header = (_generate_header_bart(text, summarizer)
                        if summarizer != "fallback"
                        else _generate_header_extractive(text))
        if _is_generic_heading(existing):
            chunk["concept_heading"] = micro_header
        chunk["micro_header"] = micro_header
        chunk["text_with_context"] = f"[{title} | {micro_header}]\n{text}"
        enriched.append(chunk)
    return enriched


def postprocess(chunks: List[Dict], document_title: Optional[str] = None,
                dedup_threshold: float = 0.92, min_words: int = 50,
                max_words: int = 300, use_bart: bool = False) -> List[Dict]:
    """
    Full post-processing pipeline:
      1. Remove intra-chunk repeated sentences
      2. Size filter
      3. Semantic deduplication  (uses shared embedder singleton)
      4. Content-based micro-header injection

    use_bart defaults to False — BART is a 1.6 GB model not worth loading
    for headers that get replaced in S3/S4. Pass use_bart=True only when
    running standalone evaluation of header quality.

    context_fringe is preserved unchanged through all steps — it is boundary
    metadata and is not affected by deduplication or size filtering.
    """
    if not chunks:
        return []
    print(f"[PostProcess] Starting with {len(chunks)} chunks...")
    chunks = remove_intra_repetition(chunks)
    chunks = filter_by_size(chunks, min_words=min_words, max_words=max_words)
    print(f"[PostProcess] After size filter: {len(chunks)} chunks")
    chunks = deduplicate_chunks(chunks, similarity_threshold=dedup_threshold)
    print(f"[PostProcess] After dedup: {len(chunks)} chunks")
    chunks = inject_micro_headers(chunks, document_title=document_title, use_bart=use_bart)
    print(f"[PostProcess] Done. Final: {len(chunks)} chunks")
    return chunks