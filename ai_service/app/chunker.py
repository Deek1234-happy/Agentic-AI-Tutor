# app/chunker.py
"""
Semantic chunking engine for the RAG pipeline.

Ported from quiz_engine.py SemanticChunker — same semantic splitting logic.

Key differences from quiz version:
  - No ChunkValidator / quality-score gating
  - No BART header generation
  - No saving to JSON / JSONL files
  - Uses quiz embedding model (all-MiniLM-L6-v2) for semantic boundary detection
  - RAG's own model (embedding.py) is used separately for vector-search
  - Output includes source_type, page_start=None, page_end=None to satisfy RAG API

Public API (unchanged call site):
    from .chunker import chunk_text
    chunks = chunk_text(text=cleaned_text, source_type="pdf")

CHANGES vs previous version:
  - min_chunk_tokens: 60  → 25   (keep useful short facts, but avoid tiny chunks)
  - max_chunk_tokens: 120 → 900  (reduce over-splitting of long NQ contexts)
  - target_chunk_tokens: 80 → 500
  - max_sentences_per_chunk: 5 → 8
  - min_words: 15 → 25
  - max_words: 350 → 400
  - dedup_similarity_threshold: 0.92 → 0.95  (less aggressive dedup)
  - chunk_text(): min_words = cfg.min_words  (removed the max() override that
    was silently inflating min_words to 36, dropping first sentences of articles)
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class ChunkingConfig:
      # Embedding model used only for semantic boundary detection
    #BAAI/bge-large-en-v1.5
    #sentence-transformers/all-MiniLM-L6-v2
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Semantic similarity
    similarity_threshold: float = 0.72
    window_size: int = 3
    breakpoint_percentile: float = 75.0

    # Dynamic (adaptive) breakpoints — recommended for mixed docs
    dynamic_similarity: bool = True
    similarity_std_factor: float = 0.75

    # Size constraints (tokens ≈ chars / 4)
    # FIX: min_chunk_tokens lowered from 60 → 15 so short but important
    #      introductory sentences are no longer silently dropped.
    min_chunk_tokens: int = 15
    max_chunk_tokens: int = 300   # was 120 ,300
    target_chunk_tokens: int = 256  # was 80 ,160

    # Sentence constraints
    min_sentence_length: int = 15
    max_sentences_per_chunk: int = 8   # was 5

    # Overlap (sentences carried over from previous chunk)
    overlap_sentences: int = 2

    # Orphan merging
    merge_orphans: bool = True

    # Post-processing
    # FIX: raised from 0.92 → 0.95 so near-duplicate but distinct chunks
    #      (e.g. first sentence vs second sentence of same article) are kept.
    dedup_similarity_threshold: float = 0.95
    min_words: int = 8    # was 15
    max_words: int = 400  # was 350



# ═══════════════════════════════════════════════════════════════
# SHARED EMBEDDING SINGLETON
# ═══════════════════════════════════════════════════════════════

_shared_embedder = None


def _get_embedder(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    global _shared_embedder
    if _shared_embedder is None:
        from sentence_transformers import SentenceTransformer
        _shared_embedder = SentenceTransformer(model_name)
    return _shared_embedder


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

_PGNUM_RE = re.compile(r"__PGNUM_(\d+)__")


def _extract_page_range(text: str):
    nums = [int(m.group(1)) for m in _PGNUM_RE.finditer(text)]
    if not nums:
        return None, None
    return min(nums), max(nums)


def _strip_page_placeholders(text: str) -> str:
    text = _PGNUM_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _is_heading(text: str) -> bool:
    t = text.strip()
    return bool(t) and len(t) <= 120 and bool(_HEADING_RE.match(t))


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


# ═══════════════════════════════════════════════════════════════
# CHUNK DATACLASS (internal use)
# ═══════════════════════════════════════════════════════════════

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
    metadata: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# SEMANTIC CHUNKER
# ═══════════════════════════════════════════════════════════════

class SemanticChunker:

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.cfg = config or ChunkingConfig()

    def chunk(self, text: str) -> List[Chunk]:
        sentences, heading_flags = self._split(text)
        if not sentences:
            return []
        embeddings = self._embed(sentences)
        similarities = self._similarities(embeddings)
        breakpoints = self._breakpoints(similarities, heading_flags)
        raw = self._build_raw(sentences, breakpoints)
        sized = self._size_constrain(raw, embeddings)
        overlapped = self._add_overlap(sized)
        return self._finalise(overlapped, embeddings)

    # ── sentence splitting ────────────────────────────────────────────────────

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

    # ── embedding ─────────────────────────────────────────────────────────────

    def _embed(self, sentences: List[str]) -> np.ndarray:
        model = _get_embedder(self.cfg.embedding_model)
        return model.encode(
            sentences,
            batch_size=64,
            show_progress_bar=len(sentences) > 100,
            normalize_embeddings=True,
        )

    # ── similarity + breakpoints ──────────────────────────────────────────────

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

    # ── chunk building ────────────────────────────────────────────────────────

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

    def _finalise(self, chunks: List[dict], embs: np.ndarray) -> List[Chunk]:
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
            final.append(Chunk(
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


# ═══════════════════════════════════════════════════════════════
# POST-PROCESSING (no BART, no JSON save)
# ═══════════════════════════════════════════════════════════════

def _remove_intra_repetition(chunks: List[Dict]) -> List[Dict]:
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


def _filter_by_size(chunks: List[Dict], min_words: int, max_words: int) -> List[Dict]:
    result = []
    for chunk in chunks:
        wc = chunk.get("word_count", len(chunk.get("text", "").split()))
        if wc < min_words or wc > max_words:
            continue
        chunk = dict(chunk)
        chunk["word_count"] = wc
        result.append(chunk)
    return result


def _deduplicate_chunks(chunks: List[Dict], similarity_threshold: float) -> List[Dict]:
    if len(chunks) <= 1:
        return chunks
    model = _get_embedder()
    embeddings = model.encode(
        [c["text"] for c in chunks],
        normalize_embeddings=True,
        batch_size=64,
    )
    kept, kept_embs = [], []
    for i, emb in enumerate(embeddings):
        if not any(_cosine(emb, k) > similarity_threshold for k in kept_embs):
            kept.append(chunks[i])
            kept_embs.append(emb)
    removed = len(chunks) - len(kept)
    if removed > 0:
        print(f"[RAG Dedup] Removed {removed} near-duplicate chunk(s).")
    return kept


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

_chunker_singleton: Optional[SemanticChunker] = None


def chunk_text(text: str, source_type: str) -> List[Dict]:
    """
    Main entry point for the RAG chunking pipeline.

    Steps:
      1. Semantic chunking via SemanticChunker (quiz embedding model)
      2. Page-number extraction from __PGNUM_N__ placeholders
      3. Noise sentence filtering
      4. Placeholder stripping from chunk text
      5. Intra-chunk repetition removal
      6. Size filtering
      7. Semantic deduplication

    Returns a list of dicts compatible with the RAG API:
      {
        "source_type":    str,
        "page_start":     int | None,
        "page_end":       int | None,
        "text":           str,
        "word_count":     int,
        "token_count":    int,
        "semantic_score": float,
      }
    """
    global _chunker_singleton
    if _chunker_singleton is None:
        _chunker_singleton = SemanticChunker(ChunkingConfig())

    cfg = _chunker_singleton.cfg

    # ── FIX ──────────────────────────────────────────────────────────────────
    # Previously this was:
    #   min_words = max(cfg.min_words, int(cfg.min_chunk_tokens * 0.6))
    # which silently overrode min_words=8 to 36 (= 60 * 0.6),
    # causing the first sentence of every Wikipedia article to be dropped.
    # ─────────────────────────────────────────────────────────────────────────
    min_words = cfg.min_words  # ← use config value directly

    print(f"[RAG Chunking] Starting semantic chunking ...", flush=True)
    raw_chunks: List[Chunk] = _chunker_singleton.chunk(text)

    output: List[Dict] = []
    skipped_empty = 0
    skipped_short = 0

    for chunk in raw_chunks:
        page_start, page_end = _extract_page_range(chunk.text)

        clean_sents = [
            s for s in chunk.sentences
            if not _is_noise(s) and len(s.split()) >= 3
        ]
        if not clean_sents:
            skipped_empty += 1
            continue

        clean_text_str = " ".join(s.strip() for s in clean_sents)
        clean_text_str = _strip_page_placeholders(clean_text_str)

        word_count = len(clean_text_str.split())
        if word_count < min_words:
            skipped_short += 1
            continue

        output.append({
            "source_type":    source_type,
            "page_start":     page_start,
            "page_end":       page_end,
            "text":           clean_text_str,
            "word_count":     word_count,
            "token_count":    chunk.token_count,
            "semantic_score": chunk.semantic_score,
        })

    print(
        f"[RAG Chunking] candidates={len(raw_chunks)}  kept={len(output)}  "
        f"skipped_empty={skipped_empty}  skipped_short={skipped_short}",
        flush=True,
    )

    # Post-process
    output = _remove_intra_repetition(output)
    output = _filter_by_size(output, min_words=cfg.min_words, max_words=cfg.max_words)
    output = _deduplicate_chunks(output, cfg.dedup_similarity_threshold)

    print(f"[RAG Chunking] Final chunks after post-processing: {len(output)}", flush=True)
    return output
