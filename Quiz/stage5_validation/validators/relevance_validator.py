"""
S5 — Stage 2: Question-Context Relevance Validation
Ensures the generated question is semantically related to the source chunk.
Uses sentence-transformers + cosine similarity.
"""

import logging
from typing import Any, Dict

from config.settings import RelevanceConfig
from utils.embeddings import EmbeddingCache

log = logging.getLogger("s5.relevance")


class RelevanceValidator:
    """
    Embeds the question and the source chunk text, then computes cosine
    similarity. MCQs with similarity below the configured threshold are
    rejected as off-topic or hallucinated.

    Why embed the question rather than compare full MCQ text?
    Because the question is the primary anchor to the source material.
    Distractors/answer are separately validated.
    """

    def __init__(self, config: RelevanceConfig, device: str = "cpu"):
        self.cfg = config
        self.cache = EmbeddingCache(device=device)

    def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        mcq_input : full S4 MCQ dict

        Returns
        -------
        {
            "passed": bool,
            "similarity_score": float,
            "threshold": float,
            "reason": str
        }
        """
        text: str = str(mcq_input.get("text", "")).strip()
        question: str = str(mcq_input.get("mcq", {}).get("question", "")).strip()

        if not text:
            return self._fail("Source chunk text is empty", 0.0)
        if not question:
            return self._fail("Question is empty", 0.0)

        # Embed both texts using shared cache
        emb_question = self.cache.encode(self.cfg.model_name, question)
        emb_chunk = self.cache.encode(self.cfg.model_name, text)

        sim = EmbeddingCache.cosine_similarity(emb_question, emb_chunk)

        log.debug("Relevance score=%.4f threshold=%.4f", sim, self.cfg.threshold)

        if sim < self.cfg.threshold:
            return self._fail(
                f"Question not sufficiently related to source chunk "
                f"(similarity={sim:.4f} < threshold={self.cfg.threshold})",
                sim,
            )

        return {
            "passed": True,
            "similarity_score": round(sim, 6),
            "threshold": self.cfg.threshold,
            "reason": "",
        }

    @staticmethod
    def _fail(reason: str, sim: float) -> Dict:
        log.debug("Relevance FAILED: %s", reason)
        return {
            "passed": False,
            "similarity_score": round(sim, 6),
            "threshold": 0.0,   # will be overwritten by caller for display
            "reason": reason,
        }
