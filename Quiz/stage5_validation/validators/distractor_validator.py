# """
# S5 — Stage 3: Distractor Validation
# Validates that wrong-answer options are:
#   (a) plausible — related to the question topic
#   (b) distinguishable — not too similar to the correct answer
# """

# import logging
# from typing import Any, Dict, List

# from config.settings import DistractorConfig
# from utils.embeddings import EmbeddingCache

# log = logging.getLogger("s5.distractors")


# class DistractorValidator:
#     """
#     For each distractor option we check two cosine-similarity conditions:

#     1. min_relevance_to_question
#        distractor vs question similarity >= threshold
#        → ensures distractors are at least on-topic
#        → rejects completely unrelated options ("the sky is blue" as a distractor
#          for a question about neural networks)

#     2. max_similarity_to_answer
#        distractor vs correct-answer similarity <= threshold
#        → ensures distractors don't basically repeat the answer
#        → rejects near-duplicate distractors that trivially reveal the answer

#     Note: very low relevance thresholds are intentional. Distractors are
#     designed to be wrong, so they won't be as close to the question as
#     the correct answer is — we just want them to be non-random.
#     """

#     def __init__(self, config: DistractorConfig, device: str = "cpu"):
#         self.cfg = config
#         self.cache = EmbeddingCache(device=device)

#     def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         Returns
#         -------
#         {
#             "passed": bool,
#             "reason": str,
#             "distractor_scores": {
#                 "B": {"relevance_to_question": 0.45, "similarity_to_answer": 0.22, "passed": True},
#                 ...
#             }
#         }
#         """
#         mcq = mcq_input.get("mcq", {})
#         question: str = str(mcq.get("question", "")).strip()
#         options: Dict[str, str] = mcq.get("options", {})
#         answer_key: str = str(mcq.get("answer", "")).strip().upper()

#         correct_answer_text: str = str(options.get(answer_key, "")).strip()
#         distractor_keys: List[str] = [k for k in ["A", "B", "C", "D"] if k != answer_key]

#         if not question or not correct_answer_text:
#             return self._fail("Question or correct answer is empty", {})

#         # Pre-encode all texts we need
#         texts_to_encode = [question, correct_answer_text] + [
#             str(options.get(k, "")).strip() for k in distractor_keys
#         ]
#         embeddings = self.cache.encode_batch(
#             self.cfg.model_name, texts_to_encode, batch_size=self.cfg.batch_size
#         )
#         emb_question = embeddings[0]
#         emb_answer = embeddings[1]
#         distractor_embeddings = embeddings[2:]

#         distractor_scores: Dict[str, Any] = {}
#         failed_distractors: List[str] = []

#         for key, emb_dist in zip(distractor_keys, distractor_embeddings):
#             dist_text = str(options.get(key, "")).strip()

#             rel_to_q = EmbeddingCache.cosine_similarity(emb_dist, emb_question)
#             sim_to_ans = EmbeddingCache.cosine_similarity(emb_dist, emb_answer)

#             # Check 1: distractor must be at least somewhat related to question
#             rel_ok = rel_to_q >= self.cfg.min_relevance_to_question
#             # Check 2: distractor must not be too similar to correct answer
#             dist_ok = sim_to_ans <= self.cfg.max_similarity_to_answer

#             passed_this = rel_ok and dist_ok
#             reason_parts = []
#             if not rel_ok:
#                 reason_parts.append(
#                     f"too unrelated to question (sim={rel_to_q:.4f} < "
#                     f"min={self.cfg.min_relevance_to_question})"
#                 )
#             if not dist_ok:
#                 reason_parts.append(
#                     f"too similar to correct answer (sim={sim_to_ans:.4f} > "
#                     f"max={self.cfg.max_similarity_to_answer})"
#                 )

#             distractor_scores[key] = {
#                 "text_preview": dist_text[:80],
#                 "relevance_to_question": round(rel_to_q, 6),
#                 "similarity_to_answer": round(sim_to_ans, 6),
#                 "passed": passed_this,
#                 "reason": "; ".join(reason_parts) if reason_parts else "",
#             }

#             if not passed_this:
#                 failed_distractors.append(key)
#                 log.debug("Distractor %s FAILED: %s", key, "; ".join(reason_parts))

#         if failed_distractors:
#             reasons = [
#                 f"Option {k}: {distractor_scores[k]['reason']}"
#                 for k in failed_distractors
#             ]
#             return {
#                 "passed": False,
#                 "reason": "Invalid distractor(s): " + " | ".join(reasons),
#                 "distractor_scores": distractor_scores,
#             }

#         log.debug("Distractor validation PASSED")
#         return {
#             "passed": True,
#             "reason": "",
#             "distractor_scores": distractor_scores,
#         }

#     @staticmethod
#     def _fail(reason: str, scores: Dict) -> Dict:
#         return {"passed": False, "reason": reason, "distractor_scores": scores}



"""
S5 — Stage 3: Distractor Validation
Validates that wrong-answer options are:
  (a) plausible — related to the question topic
  (b) distinguishable — not a paraphrase / duplicate of the correct answer

New behavior:
- Keep strong "near-miss" distractors when they are wrong but not equivalent.
- Reject only when the distractor is both very similar AND semantically equivalent
  to the correct answer.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config.settings import DistractorConfig
from utils.embeddings import EmbeddingCache

log = logging.getLogger("s5.distractors")

# NLI label order for CrossEncoder / DeBERTa NLI-style models
LABEL_CONTRADICTION = 0
LABEL_NEUTRAL = 1
LABEL_ENTAILMENT = 2


class DistractorValidator:
    """
    For each distractor option we check:

    1. min_relevance_to_question
       distractor vs question similarity >= threshold
       → ensures distractors are at least on-topic
       → rejects completely unrelated options

    2. answer equivalence guard (NLI)
       If distractor is very similar to the correct answer, we only reject it
       when it is semantically equivalent / paraphrased.
       This keeps valid near-miss distractors like inverted or swapped statements.
    """

    def __init__(self, config: DistractorConfig, device: str = "cpu"):
        self.cfg = config
        self.device = device
        self.cache = EmbeddingCache(device=device)
        self._nli_model = None

    def _resolve_nli_model_path(self) -> Optional[str]:
        """
        Prefer a local NLI model path if configured.
        If the folder does not exist, return None and fall back to cosine-only logic.
        """
        model_name = str(getattr(self.cfg, "nli_model_name", "")).strip()
        if not model_name:
            return None

        path = Path(model_name)
        if not path.exists():
            log.warning("NLI model path not found locally: %s", model_name)
            return None
        return str(path)

    def _load_nli_model(self):
        if self._nli_model is None:
            model_path = self._resolve_nli_model_path()
            if model_path is None:
                return None

            from sentence_transformers import CrossEncoder

            log.info("Loading NLI model for distractor checks from local path: %s", model_path)
            self._nli_model = CrossEncoder(
                model_path,
                device=self.device,
                activation_fn=None,
            )
        return self._nli_model

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        e = np.exp(logits - np.max(logits))
        return e / e.sum()

    def _nli_entailment_score(self, premise: str, hypothesis: str) -> Tuple[float, float, float]:
        """
        Returns (contradiction_prob, neutral_prob, entailment_prob).
        If no local NLI model is available, returns (0, 1, 0).
        """
        model = self._load_nli_model()
        if model is None:
            return 0.0, 1.0, 0.0

        logits = model.predict([(premise, hypothesis)], apply_softmax=False, show_progress_bar=False)
        probs = self._softmax(logits[0])
        return (
            float(probs[LABEL_CONTRADICTION]),
            float(probs[LABEL_NEUTRAL]),
            float(probs[LABEL_ENTAILMENT]),
        )

    def _is_semantically_equivalent(self, text_a: str, text_b: str) -> bool:
        """
        Returns True if the two texts are likely paraphrases / equivalent.
        We check both directions because entailment is directional.
        """
        if not text_a.strip() or not text_b.strip():
            return False

        _, _, entail_ab = self._nli_entailment_score(text_a, text_b)
        _, _, entail_ba = self._nli_entailment_score(text_b, text_a)

        threshold = float(getattr(self.cfg, "nli_duplicate_entailment_threshold", 0.72))
        return max(entail_ab, entail_ba) >= threshold

    def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns
        -------
        {
            "passed": bool,
            "reason": str,
            "distractor_scores": {
                "B": {"relevance_to_question": 0.45, "similarity_to_answer": 0.22, "passed": True},
                ...
            }
        }
        """
        mcq = mcq_input.get("mcq", {})
        question: str = str(mcq.get("question", "")).strip()
        options: Dict[str, str] = mcq.get("options", {})
        answer_key: str = str(mcq.get("answer", "")).strip().upper()

        correct_answer_text: str = str(options.get(answer_key, "")).strip()
        distractor_keys: List[str] = [k for k in ["A", "B", "C", "D"] if k != answer_key]

        if not question or not correct_answer_text:
            return self._fail("Question or correct answer is empty", {})

        # Pre-encode all texts we need
        texts_to_encode = [question, correct_answer_text] + [
            str(options.get(k, "")).strip() for k in distractor_keys
        ]
        embeddings = self.cache.encode_batch(
            self.cfg.model_name, texts_to_encode, batch_size=self.cfg.batch_size
        )
        emb_question = embeddings[0]
        emb_answer = embeddings[1]
        distractor_embeddings = embeddings[2:]

        distractor_scores: Dict[str, Any] = {}
        failed_distractors: List[str] = []

        # Thresholds
        min_rel = float(self.cfg.min_relevance_to_question)
        max_sim = float(self.cfg.max_similarity_to_answer)

        for key, emb_dist in zip(distractor_keys, distractor_embeddings):
            dist_text = str(options.get(key, "")).strip()

            rel_to_q = EmbeddingCache.cosine_similarity(emb_dist, emb_question)
            sim_to_ans = EmbeddingCache.cosine_similarity(emb_dist, emb_answer)

            # Gate 1: distractor must be related enough to the question
            rel_ok = rel_to_q >= min_rel
            if not rel_ok:
                distractor_scores[key] = {
                    "text_preview": dist_text[:80],
                    "relevance_to_question": round(rel_to_q, 6),
                    "similarity_to_answer": round(sim_to_ans, 6),
                    "passed": False,
                    "reason": (
                        f"too unrelated to question (sim={rel_to_q:.4f} < min={min_rel})"
                    ),
                }
                failed_distractors.append(key)
                log.debug("Distractor %s FAILED: too unrelated to question", key)
                continue

            # Gate 2: if distractor is very close to the correct answer,
            # only reject it if it is actually an equivalent/paraphrase.
            too_similar = sim_to_ans > max_sim
            equivalent = False

            if too_similar:
                equivalent = self._is_semantically_equivalent(correct_answer_text, dist_text)

            passed_this = rel_ok and (not too_similar or not equivalent)

            reason_parts = []
            if too_similar and equivalent:
                reason_parts.append(
                    f"too similar to correct answer and semantically equivalent "
                    f"(sim={sim_to_ans:.4f} > max={max_sim})"
                )
            elif too_similar and not equivalent:
                reason_parts.append(
                    f"high lexical similarity but not equivalent (sim={sim_to_ans:.4f}); kept as valid near-miss distractor"
                )

            distractor_scores[key] = {
                "text_preview": dist_text[:80],
                "relevance_to_question": round(rel_to_q, 6),
                "similarity_to_answer": round(sim_to_ans, 6),
                "passed": passed_this,
                "nli_equivalent_to_answer": equivalent if too_similar else False,
                "reason": "; ".join(reason_parts) if reason_parts else "",
            }

            if not passed_this:
                failed_distractors.append(key)
                log.debug("Distractor %s FAILED: %s", key, distractor_scores[key]["reason"])

        if failed_distractors:
            reasons = [
                f"Option {k}: {distractor_scores[k]['reason']}"
                for k in failed_distractors
            ]
            return {
                "passed": False,
                "reason": "Invalid distractor(s): " + " | ".join(reasons),
                "distractor_scores": distractor_scores,
            }

        log.debug("Distractor validation PASSED")
        return {
            "passed": True,
            "reason": "",
            "distractor_scores": distractor_scores,
        }

    @staticmethod
    def _fail(reason: str, scores: Dict) -> Dict:
        return {"passed": False, "reason": reason, "distractor_scores": scores}
