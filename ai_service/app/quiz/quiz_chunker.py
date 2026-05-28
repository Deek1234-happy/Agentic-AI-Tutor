# app/quiz/quiz_chunker.py
"""
Quiz-specific semantic chunking engine.

Differences from the RAG chunker (app/chunker.py):
  ✦  Context fringe attached to every chunk:
       prev_sentence — last sentence of the preceding chunk
       next_sentence — first sentence of the following chunk
  ✦  ChunkValidator — composite quality score gate (0.50 threshold)
  ✦  No __PGNUM_N__ handling — quiz cleaner already stripped them
  ✦  No page_start / page_end in output
  ✦  overlap_sentences = 0 (context fringe is used instead)
  ✦  Embeddings used ONLY for boundary detection; NOT stored or returned
  ✦  Stricter min_words = 35 (vs RAG's 8)

Public API:
    from .quiz_chunker import chunk_text_for_quiz
    chunks = chunk_text_for_quiz(cleaned_text)

    Returns List[Dict] with keys:
      chunk_index, text, context_prev_sentence, context_next_sentence,
      semantic_score, quality_score
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .quiz_config import QuizChunkingConfig


# ═══════════════════════════════════════════════════════════════
# SHARED EMBEDDING SINGLETON
# ═══════════════════════════════════════════════════════════════

_quiz_embedder = None


def _get_quiz_embedder(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """
    Lazy-load the sentence embedding model used for cosine-similarity
    boundary detection.  Kept as a module-level singleton so the model
    is loaded once per process, even if the endpoint is called many times.

    Note: the RAG chunker (app/chunker.py) uses its own identical singleton.
    Both point to the same cached weights on disk, so there is no extra
    download cost — only a small extra memory footprint if both are loaded
    simultaneously.
    """
    global _quiz_embedder
    if _quiz_embedder is None:
        from sentence_transformers import SentenceTransformer
        _quiz_embedder = SentenceTransformer(model_name)
    return _quiz_embedder


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

_HEADING_RE = re.compile(
    r"""^(?:
        (?:Chapter|Section|Part|Unit|Module|Step|Lecture|Appendix)\s+[\dIVXivx]+
        | (?:\d+\.)+\s*[A-Z]
        | \d+\.\s+[A-Z][a-zA-Z]
    )""",
    re.VERBOSE | re.IGNORECASE,
)

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


def _is_heading(text: str) -> bool:
    t = text.strip()
    return bool(t) and len(t) <= 120 and bool(_HEADING_RE.match(t))


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


# ═══════════════════════════════════════════════════════════════
# CHUNK DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class _QuizChunk:
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
    # Context fringe — single sentence immediately before/after this chunk's
    # boundary.  NOT part of chunk.text.  Used for metadata extraction context.
    prev_sentence: Optional[str] = None
    next_sentence: Optional[str] = None
    metadata: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# SEMANTIC CHUNKER
# ═══════════════════════════════════════════════════════════════

class _QuizSemanticChunker:
    """
    Splits cleaned text into semantically coherent chunks using cosine
    similarity on sentence embeddings.

    Algorithm:
      1. Split text into sentences (paragraph-aware regex splitter)
      2. Embed all sentences with all-MiniLM-L6-v2
      3. Compute windowed cosine similarity between adjacent sentence groups
      4. Identify breakpoints where similarity drops (dynamic mean-std method)
      5. Build raw chunks from breakpoint ranges
      6. Size-constrain (split too-large, merge orphans)
      7. Finalise: compute per-chunk semantic score
      8. Attach context fringe (prev/next boundary sentence)
    """

    def __init__(self, config: Optional[QuizChunkingConfig] = None):
        self.cfg = config or QuizChunkingConfig()

    def chunk(self, text: str) -> List[_QuizChunk]:
        sentences, heading_flags = self._split(text)
        if not sentences:
            return []
        embeddings = self._embed(sentences)
        similarities = self._similarities(embeddings)
        breakpoints = self._breakpoints(similarities, heading_flags)
        raw = self._build_raw(sentences, breakpoints)
        sized = self._size_constrain(raw, embeddings)
        overlapped = self._add_overlap(sized)
        chunks = self._finalise(overlapped, embeddings)
        return self._attach_fringe(chunks)

    # ── sentence splitting ─────────────────────────────────────────────────────

    def _split(self, text: str) -> Tuple[List[str], List[bool]]:
        sentences, flags = [], []
        for para in re.split(r"\n\n+", text):
            para = para.strip()
            if not para:
                continue
            if _is_heading(para) and len(para.split()) <= 12:
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
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"(•])", text)
        return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]

    # ── embedding ──────────────────────────────────────────────────────────────

    def _embed(self, sentences: List[str]) -> np.ndarray:
        model = _get_quiz_embedder(self.cfg.embedding_model)
        return model.encode(
            sentences,
            batch_size=64,
            show_progress_bar=len(sentences) > 100,
            normalize_embeddings=True,
        )

    # ── similarity + breakpoints ───────────────────────────────────────────────

    def _similarities(self, embs: np.ndarray) -> List[float]:
        w = self.cfg.window_size
        return [
            _cosine(_window_avg(embs, i, w), _window_avg(embs, i + 1, w))
            for i in range(len(embs) - 1)
        ]

    def _breakpoints(self, sims: List[float], heading_flags: List[bool]) -> List[int]:
        if not sims:
            return [0]
        arr = np.array(sims)
        if self.cfg.dynamic_similarity:
            threshold = np.mean(arr) - (np.std(arr) * self.cfg.similarity_std_factor)
        else:
            threshold = np.percentile(arr, 100 - self.cfg.breakpoint_percentile)
        drop_breaks = {
            i + 1 for i, s in enumerate(sims)
            if s < threshold or s < self.cfg.similarity_threshold
        }
        heading_breaks = {i for i, h in enumerate(heading_flags) if h}
        return sorted({0} | drop_breaks | heading_breaks)

    # ── chunk building ─────────────────────────────────────────────────────────

    def _build_raw(self, sentences: List[str], breakpoints: List[int]) -> List[dict]:
        chunks = []
        for j, start in enumerate(breakpoints):
            end = breakpoints[j + 1] if j + 1 < len(breakpoints) else len(sentences)
            sents = sentences[start:end]
            if len(sents) > self.cfg.max_sentences_per_chunk:
                for i in range(0, len(sents), self.cfg.max_sentences_per_chunk):
                    sub = sents[i: i + self.cfg.max_sentences_per_chunk]
                    chunks.append({
                        "sentences": sub,
                        "start": start + i,
                        "end": start + i + len(sub) - 1,
                    })
            elif sents:
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
        left  = {"sentences": sents[:split_at], "start": start, "end": start + split_at - 1}
        right = {"sentences": sents[split_at:], "start": start + split_at, "end": chunk["end"]}
        result = []
        for part in (left, right):
            if _tokens(" ".join(part["sentences"])) > self.cfg.max_chunk_tokens:
                result.extend(self._split_chunk(part, embs))
            else:
                result.append(part)
        return result

    def _add_overlap(self, chunks: List[dict]) -> List[dict]:
        """
        Quiz uses overlap_sentences=0 — context fringe handles boundary context.
        Method kept for API parity; returns chunks unchanged when n==0.
        """
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

    def _finalise(self, chunks: List[dict], embs: np.ndarray) -> List[_QuizChunk]:
        final, current_heading = [], None
        for i, c in enumerate(chunks):
            sents = c["sentences"]
            text = " ".join(sents).strip()
            if not text:
                continue
            for s in sents:
                if _is_heading(s.strip()):
                    current_heading = s.strip()
            sub = embs[c["start"]: c["end"] + 1]
            score = (
                float(np.mean([_cosine(sub[j], sub[j + 1]) for j in range(len(sub) - 1)]))
                if len(sub) >= 2 else 1.0
            )
            final.append(_QuizChunk(
                chunk_id=_chunk_id(text, i),
                index=i,
                text=text,
                sentences=sents,
                token_count=_tokens(text),
                char_count=len(text),
                start_sentence_idx=c["start"],
                end_sentence_idx=c["end"],
                heading=current_heading,
                is_table=False,
                semantic_score=round(score, 4),
            ))
        return final

    # ── context fringe ─────────────────────────────────────────────────────────

    @staticmethod
    def _first_real_sentence(sentences: List[str]) -> Optional[str]:
        """First non-empty, non-trivial sentence (single-line guard for bullets)."""
        for s in sentences:
            first_line = s.split("\n")[0].strip()
            if first_line and len(first_line.split()) >= 3:
                return first_line
        for s in sentences:
            first_line = s.split("\n")[0].strip()
            if first_line:
                return first_line
        return None

    @staticmethod
    def _last_real_sentence(sentences: List[str]) -> Optional[str]:
        """Last non-empty, non-trivial sentence (single-line guard for bullets)."""
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
    def _attach_fringe(cls, chunks: List[_QuizChunk]) -> List[_QuizChunk]:
        """
        Attach context fringe to each chunk:
          prev_sentence — last sentence of the preceding chunk
          next_sentence — first sentence of the following chunk

        First chunk → prev_sentence = None
        Last chunk  → next_sentence = None
        """
        for i, chunk in enumerate(chunks):
            chunk.prev_sentence = (
                cls._last_real_sentence(chunks[i - 1].sentences) if i > 0 else None
            )
            chunk.next_sentence = (
                cls._first_real_sentence(chunks[i + 1].sentences)
                if i < len(chunks) - 1 else None
            )
        return chunks


# ═══════════════════════════════════════════════════════════════
# CHUNK VALIDATOR
# ═══════════════════════════════════════════════════════════════

class _QuizChunkValidator:
    """
    Scores chunk quality using 5 weighted dimensions.
    Chunks below quality_score_threshold are dropped by chunk_text_for_quiz().
    """

    def __init__(self, config: Optional[QuizChunkingConfig] = None):
        self.cfg = config or QuizChunkingConfig()

    def validate(self, chunk: _QuizChunk) -> float:
        """Return composite quality score in [0, 1]."""
        scores = {
            "semantic":       self._score_semantic(chunk),
            "size":           self._score_size(chunk),
            "text_quality":   self._score_text_quality(chunk),
            "completeness":   self._score_completeness(chunk),
            "sentence_count": self._score_sentence_count(chunk),
        }
        weights = {
            "semantic": 0.30, "size": 0.20, "text_quality": 0.25,
            "completeness": 0.15, "sentence_count": 0.10,
        }
        return round(sum(scores[k] * weights[k] for k in weights), 4)

    def _score_semantic(self, chunk: _QuizChunk) -> float:
        return max(0.0, min(1.0, float(chunk.semantic_score or 0.0)))

    def _score_size(self, chunk: _QuizChunk) -> float:
        t = chunk.token_count or 0
        if t == 0:
            return 0.0
        if t < self.cfg.min_chunk_tokens:
            return 0.0
        if t > self.cfg.max_chunk_tokens:
            return 0.2
        return max(0.0, 1.0 - abs(t - self.cfg.target_chunk_tokens) / max(self.cfg.target_chunk_tokens, 1))

    def _score_text_quality(self, chunk: _QuizChunk) -> float:
        text = chunk.text or ""
        if not text:
            return 0.0
        score = 1.0
        length = max(len(text), 1)
        if sum(1 for c in text if ord(c) > 127) / length > 0.18:
            score -= 0.35
        if len(re.findall(r"[^\w\s]", text)) / length > 0.22:
            score -= 0.25
        if sum(c.isdigit() for c in text) / length > 0.40 and not chunk.is_table:
            score -= 0.2
        if re.search(r"(.)\1{6,}", text):
            score -= 0.3
        if len(text.split()) < 8:
            score -= 0.25
        return max(0.0, score)

    def _score_completeness(self, chunk: _QuizChunk) -> float:
        text = (chunk.text or "").strip()
        if not text:
            return 0.0
        score = 1.0
        if chunk.index > 0 and text[0].islower():
            score -= 0.25
        if text[-1] not in '.!?"\'»)]':
            score -= 0.2
        if re.search(r"\w-$", text):
            score -= 0.2
        return max(0.0, score)

    def _score_sentence_count(self, chunk: _QuizChunk) -> float:
        n = len(chunk.sentences)
        if n == 0:
            return 0.0
        if n < 2:
            return 0.4
        if n > 25:
            return 0.65
        return 1.0


# ═══════════════════════════════════════════════════════════════
# POST-PROCESSING HELPERS
# ═══════════════════════════════════════════════════════════════

def _remove_intra_repetition(chunks: List[Dict]) -> List[Dict]:
    """Remove repeated sentences within each chunk."""
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
        result.append(chunk)
    return result


def _filter_by_size(chunks: List[Dict], min_words: int, max_words: int) -> List[Dict]:
    """Drop chunks that are too short or too long (word count)."""
    result = []
    for chunk in chunks:
        wc = len(chunk.get("text", "").split())
        if min_words <= wc <= max_words:
            result.append(chunk)
    return result


def _deduplicate_chunks(chunks: List[Dict], threshold: float) -> List[Dict]:
    """Semantic deduplication — remove near-duplicate chunks."""
    if len(chunks) <= 1:
        return chunks
    model = _get_quiz_embedder()
    embeddings = model.encode(
        [c["text"] for c in chunks],
        normalize_embeddings=True,
        batch_size=64,
    )
    kept, kept_embs = [], []
    for i, emb in enumerate(embeddings):
        if not any(_cosine(emb, k) > threshold for k in kept_embs):
            kept.append(chunks[i])
            kept_embs.append(emb)
    removed = len(chunks) - len(kept)
    if removed > 0:
        print(f"[Quiz Dedup] Removed {removed} near-duplicate chunk(s).", flush=True)
    return kept


# ═══════════════════════════════════════════════════════════════
# SINGLETONS
# ═══════════════════════════════════════════════════════════════

_quiz_chunker_singleton: Optional[_QuizSemanticChunker] = None
_quiz_validator_singleton: Optional[_QuizChunkValidator] = None


def _init_engine() -> Tuple[_QuizSemanticChunker, _QuizChunkValidator]:
    global _quiz_chunker_singleton, _quiz_validator_singleton
    if _quiz_chunker_singleton is None:
        cfg = QuizChunkingConfig()
        _quiz_chunker_singleton = _QuizSemanticChunker(cfg)
        _quiz_validator_singleton = _QuizChunkValidator(cfg)
    return _quiz_chunker_singleton, _quiz_validator_singleton


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def chunk_text_for_quiz(text: str) -> List[Dict]:
    """
    Main entry point for the quiz chunking pipeline.

    Steps:
      1. Semantic chunking (cosine-similarity boundary detection)
      2. Per-chunk quality scoring (ChunkValidator)
      3. Drop chunks below quality_score_threshold or min_semantic_score
      4. Clean noise sentences and build final text per chunk
      5. Drop chunks below min_words word count
      6. Intra-chunk repetition removal
      7. Size filter (min_words / max_words)
      8. Semantic deduplication

    Returns List[Dict] with fields:
      chunk_index           — sequential index (0-based, re-numbered after filtering)
      text                  — clean chunk text (NO embeddings, NO page ranges)
      context_prev_sentence — last sentence of the preceding chunk (None for first)
      context_next_sentence — first sentence of the following chunk (None for last)
      semantic_score        — cosine similarity score for chunk coherence
      quality_score         — composite validator score (only >= threshold included)
    """
    chunker, validator = _init_engine()
    cfg = chunker.cfg

    print("[Quiz Chunking] Starting semantic chunking...", flush=True)
    raw_chunks = chunker.chunk(text)
    print(f"[Quiz Chunking] Raw candidates: {len(raw_chunks)}", flush=True)

    output: List[Dict] = []
    skipped_empty = skipped_quality = skipped_semantic = 0

    for chunk in raw_chunks:
        # Quality gate (validator)
        quality_score = validator.validate(chunk)
        if quality_score < cfg.quality_score_threshold:
            skipped_quality += 1
            continue

        # Semantic floor
        if chunk.semantic_score < cfg.min_semantic_score:
            skipped_semantic += 1
            continue

        # Clean noise sentences
        clean_sents = [
            s for s in chunk.sentences
            if not _is_noise(s) and len(s.split()) >= 3
        ]
        if not clean_sents:
            skipped_empty += 1
            continue

        clean_text = " ".join(s.strip() for s in clean_sents)
        word_count = len(clean_text.split())

        if word_count < cfg.min_words:
            skipped_quality += 1
            continue

        output.append({
            "text":                  clean_text,
            "context_prev_sentence": chunk.prev_sentence,
            "context_next_sentence": chunk.next_sentence,
            "semantic_score":        chunk.semantic_score,
            "quality_score":         quality_score,
        })

    print(
        f"[Quiz Chunking] candidates={len(raw_chunks)}  kept={len(output)}  "
        f"skipped_quality={skipped_quality}  skipped_semantic={skipped_semantic}  "
        f"skipped_empty={skipped_empty}",
        flush=True,
    )

    # Post-processing
    output = _remove_intra_repetition(output)
    output = _filter_by_size(output, min_words=cfg.min_words, max_words=cfg.max_words)
    output = _deduplicate_chunks(output, threshold=cfg.dedup_similarity_threshold)

    # Assign final sequential chunk_index AFTER all filtering
    for idx, chunk in enumerate(output):
        chunk["chunk_index"] = idx

    print(f"[Quiz Chunking] Final chunks after post-processing: {len(output)}", flush=True)
    return output
