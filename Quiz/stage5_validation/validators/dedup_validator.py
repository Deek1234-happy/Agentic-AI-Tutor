"""
S5 — Stage 5: Deduplication
Detects near-duplicate MCQs by comparing question embeddings
against a persistent in-memory + on-disk store.

Two MCQs are considered duplicates if their question embeddings
have cosine similarity >= threshold.

When a duplicate is found:
  - The new MCQ is rejected (the first one encountered is kept).
  - The duplicate match info is logged.

The store is saved to disk after every update so it survives
process restarts (resume support).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config.settings import DeduplicationConfig
from utils.embeddings import EmbeddingCache

log = logging.getLogger("s5.dedup")


class DeduplicationValidator:
    """
    Persistent deduplication using question embeddings.

    Store schema (JSON on disk)
    ---------------------------
    {
        "<mcq_key>": {
            "chunk_id": "...",
            "slot_index": 0,
            "question_preview": "...",
            "embedding": [0.1, 0.2, ...]   # list of floats
        },
        ...
    }
    """

    def __init__(self, config: DeduplicationConfig, device: str = "cpu"):
        self.cfg = config
        self.cache = EmbeddingCache(device=device)
        self.store_path = Path(config.persistent_store)

        # In-memory store: key -> {"embedding": np.ndarray, "meta": dict}
        self._store: Dict[str, Dict] = {}
        self._load_store()

    # ── Store persistence ─────────────────────────────────────────────────

    def _load_store(self):
        """Load existing dedup store from disk (if present)."""
        if self.store_path.exists():
            with open(self.store_path, "r") as f:
                raw = json.load(f)
            for key, entry in raw.items():
                emb = np.array(entry["embedding"], dtype=np.float32)
                self._store[key] = {
                    "embedding": emb,
                    "meta": {k: v for k, v in entry.items() if k != "embedding"},
                }
            log.info("Dedup store loaded: %d entries", len(self._store))
        else:
            log.info("Dedup store is empty (new run)")

    def _save_store(self):
        """Persist current in-memory store to disk."""
        serializable = {}
        for key, entry in self._store.items():
            serializable[key] = {
                **entry["meta"],
                "embedding": entry["embedding"].tolist(),
            }
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w") as f:
            json.dump(serializable, f)

    def _mcq_key(self, mcq_input: Dict) -> str:
        chunk_id = str(mcq_input.get("chunk_id", "unknown"))
        slot = mcq_input.get("slot_index", 0)
        return f"{chunk_id}__slot{slot}"

    # ── Validation ────────────────────────────────────────────────────────

    def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns
        -------
        {
            "passed": bool,
            "reason": str,
            "is_duplicate": bool,
            "duplicate_of": str | None,
            "similarity_score": float | None,
            "threshold": float
        }
        """
        question: str = str(mcq_input.get("mcq", {}).get("question", "")).strip()
        if not question:
            return self._fail("Question is empty", None, None)

        new_key = self._mcq_key(mcq_input)
        new_emb = self.cache.encode(self.cfg.model_name, question)

        # Compare against all stored questions
        best_match_key: Optional[str] = None
        best_sim: float = 0.0

        for stored_key, entry in self._store.items():
            if stored_key == new_key:
                # Same MCQ re-processed (resume scenario) — not a duplicate
                continue
            sim = EmbeddingCache.cosine_similarity(new_emb, entry["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_match_key = stored_key

        is_duplicate = best_sim >= self.cfg.similarity_threshold

        if is_duplicate:
            matched_meta = self._store[best_match_key]["meta"]
            reason = (
                f"Near-duplicate of MCQ '{best_match_key}' "
                f"(similarity={best_sim:.4f} >= threshold={self.cfg.similarity_threshold}). "
                f"Matched question preview: \"{matched_meta.get('question_preview', '')}...\""
            )
            log.debug("Dedup FAILED: %s", reason)
            return {
                "passed": False,
                "reason": reason,
                "is_duplicate": True,
                "duplicate_of": best_match_key,
                "duplicate_meta": matched_meta,
                "similarity_score": round(best_sim, 6),
                "threshold": self.cfg.similarity_threshold,
            }

        # Not a duplicate — register this MCQ in the store
        self._store[new_key] = {
            "embedding": new_emb,
            "meta": {
                "chunk_id": mcq_input.get("chunk_id"),
                "slot_index": mcq_input.get("slot_index", 0),
                "question_preview": question[:100],
            },
        }
        self._save_store()

        log.debug("Dedup PASSED (closest match=%.4f)", best_sim)
        return {
            "passed": True,
            "reason": "",
            "is_duplicate": False,
            "duplicate_of": None,
            "similarity_score": round(best_sim, 6) if best_match_key else None,
            "threshold": self.cfg.similarity_threshold,
        }

    def clear_store(self):
        """Wipe the dedup store (useful for testing)."""
        self._store.clear()
        if self.store_path.exists():
            self.store_path.unlink()
        log.warning("Dedup store cleared")

    @staticmethod
    def _fail(reason: str, dup_of, sim) -> Dict:
        return {
            "passed": False,
            "reason": reason,
            "is_duplicate": False,
            "duplicate_of": dup_of,
            "similarity_score": sim,
            "threshold": 0.0,
        }
