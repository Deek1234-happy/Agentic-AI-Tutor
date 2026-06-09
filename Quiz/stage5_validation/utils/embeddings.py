"""
S5 Validation Pipeline — EmbeddingCache
A thin wrapper around SentenceTransformer that:
  - caches models by name/path (avoid re-loading)
  - caches text embeddings by (model_name, text) key
  - supports batching
  - supports GPU / MPS / CPU auto-selection
  - loads models from local paths only by default
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch

log = logging.getLogger("s5.embeddings")


def _get_device(requested: Optional[str] = None) -> str:
    if requested:
        return requested
    if torch.cuda.is_available():
        log.info("Using CUDA")
        return "cuda"
    if torch.backends.mps.is_available():
        log.info("Using MPS (Apple Silicon)")
        return "mps"
    log.info("Using CPU")
    return "cpu"


class EmbeddingCache:
    """
    Process-level singleton cache for SentenceTransformer models + embeddings.

    The model_name should point to a local folder, for example:
        models/bge-large-en-v1.5

    This avoids network calls during validation.
    """

    _instance: Optional["EmbeddingCache"] = None

    def __new__(cls, device: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, device: Optional[str] = None):
        if self._initialized:
            return
        self.device = _get_device(device)
        self._models: Dict[str, object] = {}
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._initialized = True

    def _resolve_model_path(self, model_name: str) -> str:
        """
        Resolve a model path and require it to exist locally.
        This prevents Hugging Face downloads during runtime.
        """
        path = Path(model_name)
        if not path.exists():
            raise FileNotFoundError(
                f"Embedding model not found locally: {model_name}\n"
                f"Expected a local directory such as: models/bge-large-en-v1.5"
            )
        return str(path)

    def _load_model(self, model_name: str):
        """Lazy-load and cache a SentenceTransformer model from local files only."""
        if model_name not in self._models:
            from sentence_transformers import SentenceTransformer

            local_path = self._resolve_model_path(model_name)
            log.info("Loading embedding model from local path: %s", local_path)

            self._models[model_name] = SentenceTransformer(
                local_path,
                device=self.device,
            )

        return self._models[model_name]

    def _cache_key(self, model_name: str, text: str) -> str:
        raw = f"{model_name}::{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def encode(self, model_name: str, text: str) -> np.ndarray:
        """Encode a single text, using cache if available."""
        text = str(text).strip()
        key = self._cache_key(model_name, text)

        if key not in self._embedding_cache:
            model = self._load_model(model_name)
            emb = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            self._embedding_cache[key] = emb

        return self._embedding_cache[key]

    def encode_batch(
        self, model_name: str, texts: List[str], batch_size: int = 32
    ) -> List[np.ndarray]:
        """
        Encode a list of texts. Uses cache for individual items;
        only encodes those not already cached.
        """
        model = self._load_model(model_name)
        results: Dict[int, np.ndarray] = {}
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, text in enumerate(texts):
            text = str(text).strip()
            key = self._cache_key(model_name, text)
            if key in self._embedding_cache:
                results[i] = self._embedding_cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            new_embs = model.encode(
                uncached_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embs):
                key = self._cache_key(model_name, text)
                self._embedding_cache[key] = emb
                results[idx] = emb

        return [results[i] for i in range(len(texts))]

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two 1-D vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))