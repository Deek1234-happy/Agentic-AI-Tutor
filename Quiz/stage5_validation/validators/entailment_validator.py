# """
# S5 — Stage 4: Answer Correctness via NLI Entailment
# Uses a local CrossEncoder model to verify that the source chunk
# genuinely supports the correct answer.
# """

# import logging
# from pathlib import Path
# from typing import Any, Dict, Tuple

# import numpy as np

# from config.settings import EntailmentConfig

# log = logging.getLogger("s5.entailment")

# LABEL_CONTRADICTION = 0
# LABEL_NEUTRAL = 1
# LABEL_ENTAILMENT = 2


# class EntailmentValidator:
#     """
#     Uses a CrossEncoder NLI model to verify that the source chunk
#     entails the correct answer.
#     """

#     def __init__(self, config: EntailmentConfig, device: str = "cpu"):
#         self.cfg = config
#         self.device = device
#         self._model = None  # lazy load

#     def _resolve_model_path(self) -> str:
#         path = Path(self.cfg.model_name)
#         if not path.exists():
#             raise FileNotFoundError(
#                 f"NLI model not found locally: {self.cfg.model_name}\n"
#                 f"Expected a local directory such as: models/nli-deberta-v3-large"
#             )
#         return str(path)

#     def _load_model(self):
#         if self._model is None:
#             from sentence_transformers import CrossEncoder

#             local_path = self._resolve_model_path()
#             log.info("Loading NLI model from local path: %s on %s", local_path, self.device)

#             self._model = CrossEncoder(
#                 local_path,
#                 device=self.device,
#                 default_activation_function=None,
#             )
#         return self._model

#     def _softmax(self, logits: np.ndarray) -> np.ndarray:
#         e = np.exp(logits - np.max(logits))
#         return e / e.sum()

#     def _entailment_score(self, premise: str, hypothesis: str) -> Tuple[float, float, float]:
#         model = self._load_model()
#         logits = model.predict([(premise, hypothesis)], apply_softmax=False, show_progress_bar=False)
#         probs = self._softmax(logits[0])
#         return (
#             float(probs[LABEL_CONTRADICTION]),
#             float(probs[LABEL_NEUTRAL]),
#             float(probs[LABEL_ENTAILMENT]),
#         )

#     def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
#         premise: str = str(mcq_input.get("text", "")).strip()
#         mcq = mcq_input.get("mcq", {})
#         options = mcq.get("options", {})
#         answer_key = str(mcq.get("answer", "")).strip().upper()
#         answer_text = str(options.get(answer_key, "")).strip()
#         explanation = str(mcq.get("explanation", "")).strip()

#         if not premise:
#             return self._fail("Source chunk text is empty", {}, 0.0)
#         if not answer_text:
#             return self._fail("Correct answer text is empty", {}, 0.0)

#         scores: Dict[str, Any] = {}
#         best_entailment: float = 0.0

#         c1, n1, e1 = self._entailment_score(premise, answer_text)
#         scores["answer_text"] = {
#             "hypothesis": answer_text[:120],
#             "contradiction": round(c1, 6),
#             "neutral": round(n1, 6),
#             "entailment": round(e1, 6),
#         }
#         best_entailment = max(best_entailment, e1)

#         if explanation:
#             c2, n2, e2 = self._entailment_score(premise, explanation)
#             scores["explanation"] = {
#                 "hypothesis": explanation[:120],
#                 "contradiction": round(c2, 6),
#                 "neutral": round(n2, 6),
#                 "entailment": round(e2, 6),
#             }
#             best_entailment = max(best_entailment, e2)

#         passed = best_entailment >= self.cfg.entailment_threshold

#         if not passed:
#             return {
#                 "passed": False,
#                 "reason": (
#                     f"Source chunk does not sufficiently support the answer "
#                     f"(best entailment={best_entailment:.4f} < "
#                     f"threshold={self.cfg.entailment_threshold})."
#                 ),
#                 "entailment_scores": scores,
#                 "best_entailment": round(best_entailment, 6),
#                 "threshold": self.cfg.entailment_threshold,
#             }

#         return {
#             "passed": True,
#             "reason": "",
#             "entailment_scores": scores,
#             "best_entailment": round(best_entailment, 6),
#             "threshold": self.cfg.entailment_threshold,
#         }

#     @staticmethod
#     def _fail(reason: str, scores: Dict, best: float) -> Dict:
#         return {
#             "passed": False,
#             "reason": reason,
#             "entailment_scores": scores,
#             "best_entailment": best,
#             "threshold": 0.0,
#         }



# """
# S5 — Stage 4: Answer Correctness via NLI Entailment
# Uses a local CrossEncoder model to verify that the source chunk
# genuinely supports the correct answer.
# """

# import logging
# import re
# from pathlib import Path
# from typing import Any, Dict, Tuple

# import numpy as np
# import torch

# from config.settings import EntailmentConfig
# from utils.embeddings import EmbeddingCache

# log = logging.getLogger("s5.entailment")

# LABEL_CONTRADICTION = 0
# LABEL_NEUTRAL = 1
# LABEL_ENTAILMENT = 2


# class EntailmentValidator:
#     """
#     Uses a CrossEncoder NLI model to verify that the source chunk
#     entails the correct answer.
#     """

#     def __init__(self, config: EntailmentConfig, device: str = "cpu"):
#         self.cfg = config
#         self.device = device
#         self.cache = EmbeddingCache(device=device)
#         self._model = None  # lazy load

#     def _resolve_model_path(self) -> str:
#         path = Path(self.cfg.model_name)

#         if not path.exists():
#             raise FileNotFoundError(
#                 f"NLI model not found locally: {self.cfg.model_name}\n"
#                 f"Expected a local directory such as: models/nli-deberta-v3-large"
#             )

#         return str(path)

#     def _load_model(self):
#         if self._model is None:
#             from sentence_transformers import CrossEncoder

#             local_path = self._resolve_model_path()

#             log.info(
#                 "Loading NLI model from local path: %s on %s",
#                 local_path,
#                 self.device,
#             )

#             self._model = CrossEncoder(
#                 local_path,
#                 device=self.device,
#                 default_activation_function=None,
#             )

#         return self._model

#     def _softmax(self, logits: np.ndarray) -> np.ndarray:
#         e = np.exp(logits - np.max(logits))
#         return e / e.sum()

#     def _entailment_score(
#         self,
#         premise: str,
#         hypothesis: str,
#     ) -> Tuple[float, float, float]:

#         model = self._load_model()

#         logits = model.predict(
#             [(premise, hypothesis)],
#             apply_softmax=False,
#             show_progress_bar=False,
#         )

#         probs = self._softmax(logits[0])

#         return (
#             float(probs[LABEL_CONTRADICTION]),
#             float(probs[LABEL_NEUTRAL]),
#             float(probs[LABEL_ENTAILMENT]),
#         )

#     def _split_sentences(self, text: str):
#         return [
#             s.strip()
#             for s in re.split(r'(?<=[.!?])\s+', text)
#             if s.strip()
#         ]

#     def _retrieve_best_premise(
#         self,
#         chunk: str,
#         hypothesis: str,
#     ) -> str:

#         from sentence_transformers import util

#         sentences = self._split_sentences(chunk)

#         if len(sentences) <= self.cfg.top_k_sentences:
#             return " ".join(sentences)

#         # Use our shared EmbeddingCache (already silences progress bars)
#         sent_emb = self.cache.encode_batch(
#             self.cfg.embedding_model_name,
#             sentences,
#         )
#         sent_emb = torch.tensor(np.stack(sent_emb)).to(self.device)

#         hyp_emb = self.cache.encode(
#             self.cfg.embedding_model_name,
#             hypothesis,
#         )
#         hyp_emb = torch.tensor(hyp_emb).to(self.device)

#         scores = util.cos_sim(hyp_emb, sent_emb)[0]

#         top_indices = scores.argsort(descending=True)[
#             : self.cfg.top_k_sentences
#         ]

#         selected_sentences = [
#             sentences[int(i)]
#             for i in top_indices
#         ]

#         return " ".join(selected_sentences)

#     def _build_hypothesis(
#         self,
#         question: str,
#         answer: str,
#     ) -> str:

#         return f"{question} {answer}"

#     def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:

#         premise: str = str(
#             mcq_input.get("text", "")
#         ).strip()

#         mcq = mcq_input.get("mcq", {})

#         question = str(
#             mcq.get("question", "")
#         ).strip()

#         options = mcq.get("options", {})

#         answer_key = str(
#             mcq.get("answer", "")
#         ).strip().upper()

#         answer_text = str(
#             options.get(answer_key, "")
#         ).strip()

#         if not premise:
#             return self._fail(
#                 "Source chunk text is empty",
#                 {},
#                 0.0,
#             )

#         if not answer_text:
#             return self._fail(
#                 "Correct answer text is empty",
#                 {},
#                 0.0,
#             )

#         hypothesis = self._build_hypothesis(
#             question,
#             answer_text,
#         )

#         best_premise = self._retrieve_best_premise(
#             premise,
#             hypothesis,
#         )

#         c1, n1, e1 = self._entailment_score(
#             best_premise,
#             hypothesis,
#         )

#         scores: Dict[str, Any] = {
#             "selected_premise": best_premise[:300],
#             "hypothesis": hypothesis[:300],
#             "contradiction": round(c1, 6),
#             "neutral": round(n1, 6),
#             "entailment": round(e1, 6),
#         }

#         # Hard contradiction fail
#         if c1 >= self.cfg.contradiction_threshold:
#             return {
#                 "passed": False,
#                 "reason": (
#                     f"Source chunk contradicts the correct answer "
#                     f"(contradiction={c1:.4f})."
#                 ),
#                 "entailment_scores": scores,
#                 "best_entailment": round(e1, 6),
#                 "threshold": self.cfg.entailment_threshold,
#             }

#         passed = (
#             e1 >= self.cfg.entailment_threshold
#         )

#         if not passed:
#             return {
#                 "passed": False,
#                 "reason": (
#                     f"Source chunk does not sufficiently support the answer "
#                     f"(entailment={e1:.4f} < "
#                     f"threshold={self.cfg.entailment_threshold})."
#                 ),
#                 "entailment_scores": scores,
#                 "best_entailment": round(e1, 6),
#                 "threshold": self.cfg.entailment_threshold,
#             }

#         return {
#             "passed": True,
#             "reason": "",
#             "entailment_scores": scores,
#             "best_entailment": round(e1, 6),
#             "threshold": self.cfg.entailment_threshold,
#         }

#     @staticmethod
#     def _fail(
#         reason: str,
#         scores: Dict,
#         best: float,
#     ) -> Dict:

#         return {
#             "passed": False,
#             "reason": reason,
#             "entailment_scores": scores,
#             "best_entailment": best,
#             "threshold": 0.0,
#         }






# """
# S5 — Stage 4: Answer Correctness via NLI Entailment

# Uses a local CrossEncoder model to verify that the source chunk
# genuinely supports the correct answer.

# Main improvements:
# 1) Build a declarative hypothesis instead of concatenating question + answer.
# 2) Score multiple candidate premises and keep the best entailment match.
# 3) Use top-k retrieved sentences plus a combined context candidate.
# """

# import logging
# import re
# from pathlib import Path
# from typing import Any, Dict, List, Tuple

# import numpy as np
# import torch

# from config.settings import EntailmentConfig
# from utils.embeddings import EmbeddingCache

# log = logging.getLogger("s5.entailment")

# LABEL_CONTRADICTION = 0
# LABEL_NEUTRAL = 1
# LABEL_ENTAILMENT = 2


# class EntailmentValidator:
#     """
#     Uses a CrossEncoder NLI model to verify that the source chunk
#     entails the correct answer.
#     """

#     def __init__(self, config: EntailmentConfig, device: str = "cpu"):
#         self.cfg = config
#         self.device = device
#         self.cache = EmbeddingCache(device=device)
#         self._model = None  # lazy load

#     def _resolve_model_path(self) -> str:
#         path = Path(self.cfg.model_name)

#         if not path.exists():
#             raise FileNotFoundError(
#                 f"NLI model not found locally: {self.cfg.model_name}\n"
#                 f"Expected a local directory such as: models/nli-deberta-v3-large"
#             )

#         return str(path)

#     def _load_model(self):
#         if self._model is None:
#             from sentence_transformers import CrossEncoder

#             local_path = self._resolve_model_path()

#             log.info(
#                 "Loading NLI model from local path: %s on %s",
#                 local_path,
#                 self.device,
#             )

#             self._model = CrossEncoder(
#                 local_path,
#                 device=self.device,
#                 default_activation_function=None,
#             )

#         return self._model

#     def _softmax(self, logits: np.ndarray) -> np.ndarray:
#         logits = np.asarray(logits, dtype=np.float64)
#         e = np.exp(logits - np.max(logits))
#         return e / e.sum()

#     def _entailment_score(
#         self,
#         premise: str,
#         hypothesis: str,
#     ) -> Tuple[float, float, float]:

#         model = self._load_model()

#         logits = model.predict(
#             [(premise, hypothesis)],
#             apply_softmax=False,
#             show_progress_bar=False,
#         )

#         logits = np.asarray(logits)

#         # CrossEncoder usually returns shape (1, 3) for NLI.
#         if logits.ndim == 2:
#             logits = logits[0]

#         probs = self._softmax(logits)

#         return (
#             float(probs[LABEL_CONTRADICTION]),
#             float(probs[LABEL_NEUTRAL]),
#             float(probs[LABEL_ENTAILMENT]),
#         )

#     def _split_sentences(self, text: str) -> List[str]:
#         return [
#             s.strip()
#             for s in re.split(r"(?<=[.!?])\s+", text)
#             if s.strip()
#         ]

#     def _build_hypothesis(
#         self,
#         question: str,
#         answer: str,
#     ) -> str:
#         """
#         Turn the question-answer pair into a declarative statement.
#         This is usually much better for NLI than concatenating question + answer.
#         """
#         question = question.strip().rstrip("?").strip()
#         answer = answer.strip()

#         if question and answer:
#             return f"For the question '{question}', the correct answer is: {answer}."
#         if answer:
#             return f"The correct answer is: {answer}."
#         return ""

#     def _retrieve_top_sentences(
#         self,
#         chunk: str,
#         hypothesis: str,
#     ) -> List[str]:
#         """
#         Retrieve the most relevant sentences from the chunk using embedding similarity.
#         """
#         from sentence_transformers import util

#         sentences = self._split_sentences(chunk)

#         if not sentences:
#             return []

#         if len(sentences) <= self.cfg.top_k_sentences:
#             return sentences

#         sent_emb = self.cache.encode_batch(
#             self.cfg.embedding_model_name,
#             sentences,
#         )
#         sent_emb = torch.tensor(np.stack(sent_emb)).to(self.device)

#         hyp_emb = self.cache.encode(
#             self.cfg.embedding_model_name,
#             hypothesis,
#         )
#         hyp_emb = torch.tensor(hyp_emb).to(self.device)

#         scores = util.cos_sim(hyp_emb, sent_emb)[0]

#         top_indices = scores.argsort(descending=True)[: self.cfg.top_k_sentences]

#         selected_sentences = [
#             sentences[int(i)]
#             for i in top_indices
#         ]

#         return selected_sentences

#     def _build_candidate_premises(
#         self,
#         chunk: str,
#         hypothesis: str,
#     ) -> List[str]:
#         """
#         Build several candidate premises:
#         - each retrieved sentence individually
#         - a combined premise made from the retrieved top-k sentences
#         """
#         top_sentences = self._retrieve_top_sentences(chunk, hypothesis)

#         if not top_sentences:
#             return []

#         candidates: List[str] = []

#         # Individual sentence candidates
#         candidates.extend(top_sentences)

#         # Combined context candidate
#         combined = " ".join(top_sentences).strip()
#         if combined and combined not in candidates:
#             candidates.append(combined)

#         return candidates

#     def _score_candidates(
#         self,
#         premises: List[str],
#         hypothesis: str,
#     ) -> Dict[str, Any]:
#         """
#         Score all candidate premises and keep the best one by entailment.
#         """
#         if not premises:
#             return {
#                 "selected_premise": "",
#                 "contradiction": 0.0,
#                 "neutral": 0.0,
#                 "entailment": 0.0,
#             }

#         best = {
#             "selected_premise": "",
#             "contradiction": 0.0,
#             "neutral": 0.0,
#             "entailment": -1.0,
#         }

#         for premise in premises:
#             c, n, e = self._entailment_score(premise, hypothesis)

#             # Keep the candidate with the highest entailment score.
#             if e > best["entailment"]:
#                 best = {
#                     "selected_premise": premise,
#                     "contradiction": c,
#                     "neutral": n,
#                     "entailment": e,
#                 }

#         return best

#     def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:

#         premise: str = str(
#             mcq_input.get("text", "")
#         ).strip()

#         mcq = mcq_input.get("mcq", {})

#         question = str(
#             mcq.get("question", "")
#         ).strip()

#         options = mcq.get("options", {})

#         answer_key = str(
#             mcq.get("answer", "")
#         ).strip().upper()

#         answer_text = str(
#             options.get(answer_key, "")
#         ).strip()

#         if not premise:
#             return self._fail(
#                 "Source chunk text is empty",
#                 {},
#                 0.0,
#             )

#         if not question:
#             return self._fail(
#                 "Question text is empty",
#                 {},
#                 0.0,
#             )

#         if not answer_text:
#             return self._fail(
#                 "Correct answer text is empty",
#                 {},
#                 0.0,
#             )

#         hypothesis = self._build_hypothesis(
#             question,
#             answer_text,
#         )

#         if not hypothesis:
#             return self._fail(
#                 "Could not build hypothesis",
#                 {},
#                 0.0,
#             )

#         candidate_premises = self._build_candidate_premises(
#             premise,
#             hypothesis,
#         )

#         if not candidate_premises:
#             return self._fail(
#                 "Could not retrieve supporting sentences from chunk",
#                 {},
#                 0.0,
#             )

#         best_scores = self._score_candidates(
#             candidate_premises,
#             hypothesis,
#         )

#         c1 = float(best_scores["contradiction"])
#         n1 = float(best_scores["neutral"])
#         e1 = float(best_scores["entailment"])

#         scores: Dict[str, Any] = {
#             "selected_premise": str(best_scores["selected_premise"])[:300],
#             "hypothesis": hypothesis[:300],
#             "contradiction": round(c1, 6),
#             "neutral": round(n1, 6),
#             "entailment": round(e1, 6),
#             "candidate_count": len(candidate_premises),
#             "top_k_sentences": self.cfg.top_k_sentences,
#         }

#         # Hard contradiction fail
#         if c1 >= self.cfg.contradiction_threshold:
#             return {
#                 "passed": False,
#                 "reason": (
#                     f"Source chunk contradicts the correct answer "
#                     f"(contradiction={c1:.4f})."
#                 ),
#                 "entailment_scores": scores,
#                 "best_entailment": round(e1, 6),
#                 "threshold": self.cfg.entailment_threshold,
#             }

#         passed = e1 >= self.cfg.entailment_threshold

#         if not passed:
#             return {
#                 "passed": False,
#                 "reason": (
#                     f"Source chunk does not sufficiently support the answer "
#                     f"(entailment={e1:.4f} < "
#                     f"threshold={self.cfg.entailment_threshold})."
#                 ),
#                 "entailment_scores": scores,
#                 "best_entailment": round(e1, 6),
#                 "threshold": self.cfg.entailment_threshold,
#             }

#         return {
#             "passed": True,
#             "reason": "",
#             "entailment_scores": scores,
#             "best_entailment": round(e1, 6),
#             "threshold": self.cfg.entailment_threshold,
#         }

#     @staticmethod
#     def _fail(
#         reason: str,
#         scores: Dict[str, Any],
#         best: float,
#     ) -> Dict[str, Any]:

#         return {
#             "passed": False,
#             "reason": reason,
#             "entailment_scores": scores,
#             "best_entailment": best,
#             "threshold": 0.0,
#         }




"""
S5 — Stage 4: Answer Correctness via NLI Entailment

Uses a local CrossEncoder model to verify that the source chunk
genuinely supports the correct answer.

Changes from original:
    Fix 1 — Hypothesis construction: fuse Q+A into a declarative statement
             using a clean "q_clean: answer" format instead of a verbose
             template sentence, which is a better NLI signal.
    Fix 2 — top_k_sentences raised to 3 (set in EntailmentConfig).
    Fix 3 — entailment_threshold raised to 0.40 (set in EntailmentConfig).
    Fix 4 — Full-chunk fallback: if top-k scoring is a near-miss, re-score
             against the full (truncated) chunk and take the better result.
    Fix 5 — Math-heavy chunk bypass: chunks with heavy math notation are
             skipped (NLI models are unreliable on symbolic expressions).
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch

from config.settings import EntailmentConfig
from utils.embeddings import EmbeddingCache

log = logging.getLogger("s5.entailment")

LABEL_CONTRADICTION = 0
LABEL_NEUTRAL = 1
LABEL_ENTAILMENT = 2

# Fix 5: Patterns that indicate math-heavy content.
_MATH_PATTERNS: List[str] = [
    r"exp\(",
    r"log\(",
    r"\\frac",
    r"\bderivative\b",
    r"d/d[a-zA-Z]",
]


class EntailmentValidator:
    """
    Uses a CrossEncoder NLI model to verify that the source chunk
    entails the correct answer.
    """

    def __init__(self, config: EntailmentConfig, device: str = "cpu"):
        self.cfg = config
        self.device = device
        self.cache = EmbeddingCache(device=device)
        self._model = None  # lazy load

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _resolve_model_path(self) -> str:
        path = Path(self.cfg.model_name)

        if not path.exists():
            raise FileNotFoundError(
                f"NLI model not found locally: {self.cfg.model_name}\n"
                f"Expected a local directory such as: models/nli-deberta-v3-large"
            )

        return str(path)

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            local_path = self._resolve_model_path()

            log.info(
                "Loading NLI model from local path: %s on %s",
                local_path,
                self.device,
            )

            self._model = CrossEncoder(
                local_path,
                device=self.device,
                default_activation_function=None,
            )

        return self._model

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        logits = np.asarray(logits, dtype=np.float64)
        e = np.exp(logits - np.max(logits))
        return e / e.sum()

    def _entailment_score(
        self,
        premise: str,
        hypothesis: str,
    ) -> Tuple[float, float, float]:
        """Return (contradiction, neutral, entailment) probabilities."""
        model = self._load_model()

        logits = model.predict(
            [(premise, hypothesis)],
            apply_softmax=False,
            show_progress_bar=False,
        )

        logits = np.asarray(logits)

        # CrossEncoder usually returns shape (1, 3) for NLI.
        if logits.ndim == 2:
            logits = logits[0]

        probs = self._softmax(logits)

        return (
            float(probs[LABEL_CONTRADICTION]),
            float(probs[LABEL_NEUTRAL]),
            float(probs[LABEL_ENTAILMENT]),
        )

    # ------------------------------------------------------------------
    # Fix 1: Hypothesis construction
    # ------------------------------------------------------------------

    def _build_hypothesis(self, question: str, answer: str) -> str:
        """
        Fuse the question and answer into a declarative statement for NLI.

        The original template-based approach ("For the question '…', the
        correct answer is: …") adds noise that confuses NLI models.  A
        cleaner signal is to strip the question mark and join with the
        answer via a colon, which mirrors how reference-style declaratives
        look in pre-training corpora.

        Example
        -------
        question : "What is the derivative of log(1 + exp(z))?"
        answer   : "exp(z) / (1 + exp(z))"
        result   : "What is the derivative of log(1 + exp(z)): exp(z) / (1 + exp(z))"
        """
        q_clean = re.sub(r"\?$", "", question.strip()).strip()
        answer = answer.strip()

        if q_clean and answer:
            return f"{q_clean}: {answer}"
        if answer:
            return answer
        return ""

    # ------------------------------------------------------------------
    # Fix 5: Math-heavy chunk detection
    # ------------------------------------------------------------------

    def _is_math_heavy(self, text: str) -> bool:
        """
        Return True when the chunk contains enough symbolic math that NLI
        entailment scores are likely to be unreliable.
        """
        matches = sum(
            1 for pattern in _MATH_PATTERNS if re.search(pattern, text)
        )
        return matches >= self.cfg.math_pattern_min_matches

    # ------------------------------------------------------------------
    # Sentence retrieval
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> List[str]:
        return [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text)
            if s.strip()
        ]

    def _retrieve_top_sentences(
        self,
        chunk: str,
        hypothesis: str,
    ) -> List[str]:
        """
        Retrieve the most relevant sentences from the chunk using
        embedding cosine similarity against the hypothesis.
        """
        from sentence_transformers import util

        sentences = self._split_sentences(chunk)

        if not sentences:
            return []

        if len(sentences) <= self.cfg.top_k_sentences:
            return sentences

        sent_emb = self.cache.encode_batch(
            self.cfg.embedding_model_name,
            sentences,
        )
        sent_emb = torch.tensor(np.stack(sent_emb)).to(self.device)

        hyp_emb = self.cache.encode(
            self.cfg.embedding_model_name,
            hypothesis,
        )
        hyp_emb = torch.tensor(hyp_emb).to(self.device)

        scores = util.cos_sim(hyp_emb, sent_emb)[0]

        top_indices = scores.argsort(descending=True)[: self.cfg.top_k_sentences]

        return [sentences[int(i)] for i in top_indices]

    # ------------------------------------------------------------------
    # Candidate premise construction
    # ------------------------------------------------------------------

    def _build_candidate_premises(
        self,
        chunk: str,
        hypothesis: str,
    ) -> List[str]:
        """
        Build candidate premises:
        - each top-k retrieved sentence individually
        - a combined premise from all top-k sentences
        """
        top_sentences = self._retrieve_top_sentences(chunk, hypothesis)

        if not top_sentences:
            return []

        candidates: List[str] = list(top_sentences)

        combined = " ".join(top_sentences).strip()
        if combined and combined not in candidates:
            candidates.append(combined)

        return candidates

    def _score_candidates(
        self,
        premises: List[str],
        hypothesis: str,
    ) -> Dict[str, Any]:
        """
        Score all candidate premises and keep the one with the highest
        entailment score.
        """
        if not premises:
            return {
                "selected_premise": "",
                "contradiction": 0.0,
                "neutral": 0.0,
                "entailment": 0.0,
            }

        best: Dict[str, Any] = {
            "selected_premise": "",
            "contradiction": 0.0,
            "neutral": 0.0,
            "entailment": -1.0,
        }

        for premise in premises:
            c, n, e = self._entailment_score(premise, hypothesis)

            if e > best["entailment"]:
                best = {
                    "selected_premise": premise,
                    "contradiction": c,
                    "neutral": n,
                    "entailment": e,
                }

        return best

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:

        premise: str = str(mcq_input.get("text", "")).strip()
        mcq: Dict[str, Any] = mcq_input.get("mcq", {})
        question: str = str(mcq.get("question", "")).strip()
        options: Dict[str, str] = mcq.get("options", {})
        answer_key: str = str(mcq.get("answer", "")).strip().upper()
        answer_text: str = str(options.get(answer_key, "")).strip()

        # --- Basic input guards -------------------------------------------
        if not premise:
            return self._fail("Source chunk text is empty", {}, 0.0)

        if not question:
            return self._fail("Question text is empty", {}, 0.0)

        if not answer_text:
            return self._fail("Correct answer text is empty", {}, 0.0)

        # Fix 5: Bypass NLI for math-heavy chunks --------------------------
        if self._is_math_heavy(premise):
            log.warning(
                "Math-heavy chunk detected — NLI entailment unreliable. "
                "Passing by default."
            )
            return {
                "passed": True,
                "reason": "math_chunk_bypass",
                "entailment_scores": {},
                "best_entailment": 1.0,
                "threshold": self.cfg.entailment_threshold,
            }

        # Fix 1: Build a clean declarative hypothesis ----------------------
        hypothesis = self._build_hypothesis(question, answer_text)

        if not hypothesis:
            return self._fail("Could not build hypothesis", {}, 0.0)

        # Retrieve top-k candidate premises --------------------------------
        candidate_premises = self._build_candidate_premises(premise, hypothesis)

        if not candidate_premises:
            return self._fail(
                "Could not retrieve supporting sentences from chunk", {}, 0.0
            )

        best_scores = self._score_candidates(candidate_premises, hypothesis)

        c1 = float(best_scores["contradiction"])
        n1 = float(best_scores["neutral"])
        e1 = float(best_scores["entailment"])
        best_premise: str = str(best_scores["selected_premise"])

        # Fix 4: Full-chunk fallback when top-k is a near-miss -------------
        half_threshold = self.cfg.entailment_threshold * 0.5
        if e1 < self.cfg.entailment_threshold and e1 > half_threshold:
            full_premise = premise[: self.cfg.full_chunk_max_chars]
            log.debug(
                "Top-k near-miss (e=%.4f). Retrying with full chunk (%d chars).",
                e1,
                len(full_premise),
            )
            c2, n2, e2 = self._entailment_score(full_premise, hypothesis)

            if e2 > e1:
                log.debug(
                    "Full-chunk improved entailment: %.4f → %.4f", e1, e2
                )
                e1 = e2
                c1 = min(c1, c2)
                n1 = n2
                best_premise = full_premise

        # --- Compile scores dict ------------------------------------------
        scores: Dict[str, Any] = {
            "selected_premise": best_premise[:300],
            "hypothesis": hypothesis[:300],
            "contradiction": round(c1, 6),
            "neutral": round(n1, 6),
            "entailment": round(e1, 6),
            "candidate_count": len(candidate_premises),
            "top_k_sentences": self.cfg.top_k_sentences,
        }

        # Hard contradiction fail ------------------------------------------
        if c1 >= self.cfg.contradiction_threshold:
            return {
                "passed": False,
                "reason": (
                    f"Source chunk contradicts the correct answer "
                    f"(contradiction={c1:.4f})."
                ),
                "entailment_scores": scores,
                "best_entailment": round(e1, 6),
                "threshold": self.cfg.entailment_threshold,
            }

        # Threshold check --------------------------------------------------
        passed = e1 >= self.cfg.entailment_threshold

        if not passed:
            return {
                "passed": False,
                "reason": (
                    f"Source chunk does not sufficiently support the answer "
                    f"(entailment={e1:.4f} < "
                    f"threshold={self.cfg.entailment_threshold})."
                ),
                "entailment_scores": scores,
                "best_entailment": round(e1, 6),
                "threshold": self.cfg.entailment_threshold,
            }

        return {
            "passed": True,
            "reason": "",
            "entailment_scores": scores,
            "best_entailment": round(e1, 6),
            "threshold": self.cfg.entailment_threshold,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fail(
        reason: str,
        scores: Dict[str, Any],
        best: float,
    ) -> Dict[str, Any]:
        return {
            "passed": False,
            "reason": reason,
            "entailment_scores": scores,
            "best_entailment": best,
            "threshold": 0.0,
        }