# """
# RAG Evaluation Pipeline — wired to YOUR system
# ================================================
# Uses your exact:
#   - answer_question()  from app/rag_service.py  (retrieval + rerank + Groq generation)
#   - No OpenAI, no new retrieval — everything goes through your existing code.

# New features:
#   - Rate limiter        : stays under Groq's RPM limit (default 30 req/min)
#   - Checkpoints         : saves progress every 10 questions → safe to resume
#   - Default limit=50    : evaluates first 50 questions out of the box

# Usage (run from your project root where /app lives):
# -----------------------------------------------------
#     python rag_eval_pipeline.py --input your_eval_results.json
#     python rag_eval_pipeline.py --input your_eval_results.json --rpm 30 --limit 50
#     python rag_eval_pipeline.py --input your_eval_results.json --resume   # skip already-done questions

# Arguments:
#     --input      Path to your retrieval eval JSON  (list of question objects)
#     --output     Output CSV path                   (default: rag_eval_output.csv)
#     --top_k      top_k passed to answer_question   (default: 5)
#     --limit      Evaluate first N questions        (REQUIRED, e.g. --limit 50)
#     --rpm        Groq requests per minute budget   (default: 30)
#     --checkpoint Every N questions save progress   (default: 10)
#     --resume     Skip questions already in --output CSV and continue from there
# """

# import argparse
# import csv
# import json
# import os
# import re
# import string
# import sys
# import time
# from collections import Counter, deque
# from typing import List, Dict, Any, Tuple, Optional

# # ── tqdm is optional ──────────────────────────────────────────────────────────
# try:
#     from tqdm import tqdm
# except ImportError:
#     def tqdm(iterable, **kwargs):
#         total = kwargs.get("total", "?")
#         desc  = kwargs.get("desc", "")
#         for i, item in enumerate(iterable, 1):
#             print(f"\r{desc}: {i}/{total}", end="", flush=True)
#             yield item
#         print()


# # ── Import YOUR rag_service ───────────────────────────────────────────────────
# try:
#     from app.rag_service import answer_question, IDK_MESSAGE
# except ModuleNotFoundError as e:
#     sys.exit(
#         f"\n[ERROR] Could not import your app: {e}\n"
#         "Run this script from your project root directory, e.g.:\n"
#         "    python rag_eval_pipeline.py --input data.json\n"
#     )


# # ══════════════════════════════════════════════════════════════════════════════
# # 1.  RATE LIMITER
# #     Sliding-window tracker: keeps timestamps of the last `rpm` calls.
# #     Before each call it sleeps just long enough to stay under the limit.
# # ══════════════════════════════════════════════════════════════════════════════

# class RateLimiter:
#     """
#     Sliding-window rate limiter for Groq RPM.

#     Usage:
#         limiter = RateLimiter(rpm=30)
#         limiter.wait()          # call before every answer_question()
#         limiter.record()        # call right after
#     """

#     def __init__(self, rpm: int = 30):
#         self.rpm      = rpm
#         self.window   = 60.0          # 1 minute window
#         self.calls    : deque = deque()   # timestamps of recent calls
#         self._req_count = 0           # total requests made (for reporting)
#         self._wait_total = 0.0        # total seconds spent waiting

#     def wait(self) -> float:
#         """Block until it is safe to make the next request. Returns sleep time."""
#         now = time.time()

#         # Drop timestamps older than 1 minute
#         while self.calls and now - self.calls[0] >= self.window:
#             self.calls.popleft()

#         if len(self.calls) >= self.rpm:
#             # Oldest call in window; must wait until it falls out
#             sleep_for = self.window - (now - self.calls[0]) + 0.05  # small buffer
#             if sleep_for > 0:
#                 print(f"\n  ⏳  Rate limit: {len(self.calls)}/{self.rpm} req/min — "
#                       f"waiting {sleep_for:.1f}s …", flush=True)
#                 time.sleep(sleep_for)
#                 self._wait_total += sleep_for
#             return sleep_for
#         return 0.0

#     def record(self):
#         """Record that a request was just made."""
#         self.calls.append(time.time())
#         self._req_count += 1

#     def report(self) -> Dict[str, Any]:
#         return {
#             "total_requests":    self._req_count,
#             "total_wait_sec":    round(self._wait_total, 2),
#             "avg_wait_per_req":  round(self._wait_total / max(self._req_count, 1), 2),
#             "rpm_budget":        self.rpm,
#         }


# # ══════════════════════════════════════════════════════════════════════════════
# # 2.  TEXT NORMALISATION
# # ══════════════════════════════════════════════════════════════════════════════

# def normalize(text: str) -> str:
#     text = text.lower()
#     text = re.sub(r"\b(a|an|the)\b", " ", text)
#     text = text.translate(str.maketrans("", "", string.punctuation))
#     return " ".join(text.split())


# def tokenize(text: str) -> List[str]:
#     return normalize(text).split()


# # ══════════════════════════════════════════════════════════════════════════════
# # 3.  GENERATION QUALITY  — token-level P / R / F1  (paper-style)
# # ══════════════════════════════════════════════════════════════════════════════

# def token_prf(prediction: str, gold_answers: List[str]) -> Dict[str, float]:
#     pred_tokens = tokenize(prediction)
#     best_p = best_r = best_f1 = 0.0

#     for gold in gold_answers:
#         gold_tokens = tokenize(gold)
#         if not pred_tokens and not gold_tokens:
#             p = r = f1 = 1.0
#         elif not pred_tokens or not gold_tokens:
#             p = r = f1 = 0.0
#         else:
#             common     = Counter(pred_tokens) & Counter(gold_tokens)
#             num_common = sum(common.values())
#             p  = num_common / len(pred_tokens)
#             r  = num_common / len(gold_tokens)
#             f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
#         if f1 > best_f1:
#             best_p, best_r, best_f1 = p, r, f1

#     return {
#         "precision": round(best_p  * 100, 2),
#         "recall":    round(best_r  * 100, 2),
#         "f1":        round(best_f1 * 100, 2),
#     }


# # ══════════════════════════════════════════════════════════════════════════════
# # 4.  ANSWER CORRECTNESS
# # ══════════════════════════════════════════════════════════════════════════════

# def exact_match(prediction: str, gold_answers: List[str]) -> int:
#     pred_norm = normalize(prediction)
#     return int(any(normalize(g) == pred_norm for g in gold_answers))


# def contains_match(prediction: str, gold_answers: List[str]) -> int:
#     pred_norm = normalize(prediction)
#     return int(any(normalize(g) in pred_norm for g in gold_answers))


# # ══════════════════════════════════════════════════════════════════════════════
# # 5.  FAITHFULNESS  (mirrors your _verify_answer_in_context)
# # ══════════════════════════════════════════════════════════════════════════════

# def faithfulness_score(answer: str, context: str) -> Tuple[str, float]:
#     answer_lc  = answer.lower()
#     context_lc = context.lower()

#     if IDK_MESSAGE.lower() in answer_lc or "don't know" in answer_lc:
#         return "IDK/FAITHFUL", 1.0

#     answer_words = [w for w in tokenize(answer) if len(w) > 4]
#     if not answer_words:
#         return "NOT_FAITHFUL", 0.0

#     matches = sum(1 for w in answer_words if w in context_lc)
#     ratio   = matches / len(answer_words)
#     verdict = "FAITHFUL" if ratio >= 0.3 else "NOT_FAITHFUL"
#     return verdict, round(ratio, 3)


# # ══════════════════════════════════════════════════════════════════════════════
# # 6.  CHUNK HELPERS
# #     Tuple format: (id, document_id, chunk_text, page_start, page_end, score)
# # ══════════════════════════════════════════════════════════════════════════════

# def chunks_to_context(chunks: List[Tuple]) -> str:
#     return "\n\n".join(
#         c[2].strip() for c in chunks if len(c) > 2 and c[2] and c[2].strip()
#     )


# def avg_chunk_score(chunks: List[Tuple]) -> Optional[float]:
#     scores = [c[5] for c in chunks if len(c) > 5]
#     return round(sum(scores) / len(scores), 4) if scores else None


# # ══════════════════════════════════════════════════════════════════════════════
# # 7.  CHECKPOINT HELPERS
# # ══════════════════════════════════════════════════════════════════════════════

# def load_checkpoint(output_path: str) -> Tuple[List[Dict], set]:
#     """
#     Load already-completed rows from JSON checkpoint.
#     Returns (rows, done_question_ids).
#     """

#     rows: List[Dict] = []
#     done_ids: set = set()

#     if not os.path.exists(output_path):
#         return rows, done_ids

#     try:
#         with open(output_path, "r", encoding="utf-8") as f:
#             rows = json.load(f)

#         for row in rows:
#             if row.get("question_id"):
#                 done_ids.add(row["question_id"])

#         print(
#             f"  ↩️  Resumed: found {len(rows)} already-completed questions in {output_path}"
#         )

#     except Exception as e:
#         print(f"  ⚠️  Could not read checkpoint file ({e}), starting fresh.")

#     return rows, done_ids


# def save_checkpoint(output_path: str,
#                     rows: List[Dict],
#                     label: str = "") -> None:
#     """
#     Save checkpoint as JSON.
#     """

#     if not rows:
#         return

#     with open(output_path, "w", encoding="utf-8") as f:
#         json.dump(rows, f, indent=2)

#     tag = f" [{label}]" if label else ""

#     print(
#         f"  💾  Checkpoint saved{tag} → "
#         f"{output_path}  ({len(rows)} rows)"
#     )
# # ══════════════════════════════════════════════════════════════════════════════
# # 8.  CHECKPOINT SUMMARY  (prints running metrics at each checkpoint)
# # ══════════════════════════════════════════════════════════════════════════════

# def print_checkpoint_summary(rows: List[Dict], checkpoint_n: int) -> None:
#     """Print rolling metrics over the rows evaluated so far."""

#     def _f(key, cast=float):
#         vals = []
#         for r in rows:
#             v = r.get(key)
#             if v not in (None, "", "n/a"):
#                 try:
#                     vals.append(cast(v))
#                 except (ValueError, TypeError):
#                     pass
#         return round(sum(vals) / len(vals), 2) if vals else "n/a"

#     sep = "-" * 52
#     print(f"\n{sep}")
#     print(f"  📌  CHECKPOINT  — questions 1–{len(rows)}  (every {checkpoint_n})")
#     print(sep)
#     print(f"  Gen Precision  : {_f('gen_precision')}%")
#     print(f"  Gen Recall     : {_f('gen_recall')}%")
#     print(f"  Gen F1         : {_f('gen_f1')}%")
#     print(f"  Exact Match    : {_f('exact_match')}")
#     print(f"  Contains Match : {_f('contains_match')}")
#     print(f"  Faithful rate  : {_f('faithful_binary')}")
#     print(f"  Avg gen latency: {_f('gen_latency_ms')} ms")
#     print(sep + "\n")


# # ══════════════════════════════════════════════════════════════════════════════
# # 9.  MAIN PIPELINE
# # ══════════════════════════════════════════════════════════════════════════════

# def run_pipeline(input_path:      str,
#                  output_path:     str,
#                  top_k:           int,
#                  limit:           int,
#                  rpm:             int,
#                  checkpoint_every: int,
#                  resume:          bool) -> None:

#     # ── Load JSON ─────────────────────────────────────────────────────────────
#     with open(input_path, "r", encoding="utf-8") as f:
#         data: List[Dict[str, Any]] = json.load(f)

#     if isinstance(data, dict):
#         data = next(v for v in data.values() if isinstance(v, list))

#     # Always cap at `limit` (default 50)
#     data = data[:limit]

#     # ── Resume from checkpoint ────────────────────────────────────────────────
#     if resume:
#         rows, done_ids = load_checkpoint(output_path)
#     else:
#         rows, done_ids = [], set()

#     # ── Rate limiter ──────────────────────────────────────────────────────────
#     limiter = RateLimiter(rpm=rpm)

#     # ── Aggregation buckets ───────────────────────────────────────────────────
#     agg: Dict[str, list] = {
#         "precision":          [],
#         "recall":             [],
#         "f1":                 [],
#         "exact_match":        [],
#         "contains_match":     [],
#         "faithful":           [],
#         "overlap_ratio":      [],
#         "num_chunks":         [],
#         "avg_chunk_score":    [],
#         "gen_latency_ms":     [],
#         "wait_sec":           [],
#         "retrieval_hit_at_k": [],
#         "retrieval_mrr":      [],
#         "retrieval_latency":  [],
#     }

#     # Pre-fill agg from resumed rows so checkpoint summaries stay accurate
#     for r in rows:
#         def _safe(key, cast=float):
#             v = r.get(key)
#             try:    return cast(v) if v not in (None, "") else None
#             except: return None

#         for key in ("precision","recall","f1","exact_match","contains_match",
#                     "faithful_binary","overlap_ratio","num_chunks_retrieved",
#                     "avg_chunk_score","gen_latency_ms",
#                     "retrieval_hit_at_k","retrieval_mrr","retrieval_latency_ms"):
#             dest = {
#                 "faithful_binary":      "faithful",
#                 "num_chunks_retrieved": "num_chunks",
#                 "retrieval_latency_ms": "retrieval_latency",
#             }.get(key, key)
#             v = _safe(key)
#             if v is not None and dest in agg:
#                 agg[dest].append(v)

#     todo = [item for item in data
#             if item.get("question_id", "") not in done_ids]

#     total_to_do = len(todo)
#     skipped     = len(rows)

#     print(f"\n🚀  Evaluating {total_to_do} questions  "
#           f"(limit={limit}, top_k={top_k}, rpm={rpm}, "
#           f"checkpoint every {checkpoint_every})")
#     if skipped:
#         print(f"    ↩️  Skipping {skipped} already-done questions\n")
#     else:
#         print()

#     eval_start = time.time()

#     for idx, item in enumerate(tqdm(todo, desc="Evaluating", total=total_to_do), 1):

#         qid      = item.get("question_id", "")
#         question = item["question"]
#         golds    = item["answers"]

#         # ── Rate limit: wait if needed, then call YOUR system ─────────────────
#         wait_sec = limiter.wait()
#         t0       = time.time()
#         answer, chunks = answer_question(question, top_k=top_k)
#         limiter.record()
#         gen_latency = round((time.time() - t0) * 1000, 1)

#         # ── Metrics ───────────────────────────────────────────────────────────
#         context        = chunks_to_context(chunks)
#         prf            = token_prf(answer, golds)
#         em             = exact_match(answer, golds)
#         cm             = contains_match(answer, golds)
#         faith, overlap = faithfulness_score(answer, context)
#         faithful_bin   = 1 if "FAITHFUL" in faith else 0
#         avg_score      = avg_chunk_score(chunks)

#         hit_at_k    = item.get("hit_at_k", item.get("hit_at_1"))
#         mrr         = item.get("mrr")
#         ret_latency = item.get("latency_ms")

#         row = {
#                 "question_id": qid,
#                 "question": question,
#                 "gold_answers": golds,
#                 "generated_answer": answer,

#                 "retrieved_chunks": [
#                     {
#                         "document_id": str(c[1]),
#                         "chunk_text": c[2],
#                         "page_start": c[3],
#                         "page_end": c[4],
#                         "score": c[5],
#                     }
#                     for c in chunks
#                 ],

#                 "gen_precision": prf["precision"],
#                 "gen_recall": prf["recall"],
#                 "gen_f1": prf["f1"],

#                 "exact_match": em,
#                 "contains_match": cm,

#                 "faithful_verdict": faith,
#                 "faithful_binary": faithful_bin,
#                 "context_overlap_ratio": overlap,

#                 "num_chunks_retrieved": len(chunks),
#                 "avg_chunk_score": avg_score,

#                 "gen_latency_ms": gen_latency,
#                 "rate_wait_sec": round(wait_sec, 2),

#                 "retrieval_hit_at_k": hit_at_k,
#                 "retrieval_mrr": mrr,
#                 "retrieval_latency_ms": ret_latency,
#             }
#         rows.append(row)

#         # accumulate
#         agg["precision"].append(prf["precision"])
#         agg["recall"].append(prf["recall"])
#         agg["f1"].append(prf["f1"])
#         agg["exact_match"].append(em)
#         agg["contains_match"].append(cm)
#         agg["faithful"].append(faithful_bin)
#         agg["overlap_ratio"].append(overlap)
#         agg["num_chunks"].append(len(chunks))
#         agg["gen_latency_ms"].append(gen_latency)
#         agg["wait_sec"].append(wait_sec)
#         if avg_score   is not None: agg["avg_chunk_score"].append(avg_score)
#         if hit_at_k    is not None: agg["retrieval_hit_at_k"].append(hit_at_k)
#         if mrr         is not None: agg["retrieval_mrr"].append(mrr)
#         if ret_latency is not None: agg["retrieval_latency"].append(ret_latency)

#         # ── Checkpoint every N questions ──────────────────────────────────────
#         if idx % checkpoint_every == 0:
#             print_checkpoint_summary(rows, checkpoint_every)
#             save_checkpoint(output_path, rows,
#                             label=f"q{skipped + idx}/{skipped + total_to_do}")

#     # ── Final save ────────────────────────────────────────────────────────────
#     save_checkpoint(output_path, rows, label="FINAL")

#     def avg(lst: list):
#         return round(sum(lst) / len(lst), 2) if lst else "n/a"

#     elapsed_min = round((time.time() - eval_start) / 60, 2)
#     rate_report = limiter.report()
#     n = len(rows)
#     FINAL_METRICS_FILE = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/final_rag_metrics.json"

#     final_metrics = {
#         "generation_quality": {
#             "precision": avg(agg['precision']),
#             "recall": avg(agg['recall']),
#             "f1": avg(agg['f1']),
#         },

#         "answer_correctness": {
#             "exact_match": avg(agg['exact_match']),
#             "contains_match": avg(agg['contains_match']),
#         },

#         "faithfulness": {
#             "faithful_rate": avg(agg['faithful']),
#             "avg_overlap": avg(agg['overlap_ratio']),
#         },

#         "retrieval_live_system": {
#             "avg_chunks_retrieved": avg(agg['num_chunks']),
#             "avg_chunk_score": avg(agg['avg_chunk_score']),
#         },

#         "retrieval_eval_json": {
#             "hit_at_k": avg(agg['retrieval_hit_at_k']),
#             "mrr": avg(agg['retrieval_mrr']),
#             "retrieval_latency_ms": avg(agg['retrieval_latency']),
#         },

#         "latency_and_rate_limit": {
#             "avg_generation_latency_ms": avg(agg['gen_latency_ms']),
#             "total_elapsed_min": elapsed_min,
#             "rpm_budget": rate_report['rpm_budget'],
#             "total_requests": rate_report['total_requests'],
#             "total_wait_sec": rate_report['total_wait_sec'],
#             "avg_wait_per_request_sec": rate_report['avg_wait_per_req'],
#         },

#         "evaluation_info": {
#             "num_questions": n,
#             "top_k": top_k,
#         }
#     }

#     with open(FINAL_METRICS_FILE, "w", encoding="utf-8") as f:
#         json.dump(final_metrics, f, indent=4)

#     print(f"\n📁 Final metrics saved → {FINAL_METRICS_FILE}")

#     # ══════════════════════════════════════════════════════════════════════════
#     # 10.  FINAL SUMMARY
#     # ══════════════════════════════════════════════════════════════════════════

  
#     sep = "=" * 58
#     print(f"\n{sep}")
#     print(f"  RAG EVALUATION SUMMARY  (n={n} questions, top_k={top_k})")
#     print(sep)

#     print("\n📊  Generation Quality  (token-level, paper-style)")
#     print(f"    Precision : {avg(agg['precision'])}%")
#     print(f"    Recall    : {avg(agg['recall'])}%")
#     print(f"    F1        : {avg(agg['f1'])}%")

#     print("\n✅  Answer Correctness")
#     print(f"    Exact Match    : {avg(agg['exact_match'])}")
#     print(f"    Contains Match : {avg(agg['contains_match'])}")

#     print("\n🔍  Faithfulness  (context-overlap ≥ 0.3)")
#     print(f"    Faithful rate  : {avg(agg['faithful'])}")
#     print(f"    Avg overlap    : {avg(agg['overlap_ratio'])}")

#     print("\n📥  Retrieval  (live system)")
#     print(f"    Avg chunks retrieved : {avg(agg['num_chunks'])}")
#     print(f"    Avg chunk score      : {avg(agg['avg_chunk_score'])}")

#     if agg["retrieval_hit_at_k"]:
#         print("\n📥  Retrieval  (from your eval JSON)")
#         print(f"    Hit@K             : {avg(agg['retrieval_hit_at_k'])}")
#         print(f"    MRR               : {avg(agg['retrieval_mrr'])}")
#         print(f"    Retrieval latency : {avg(agg['retrieval_latency'])} ms")

#     print("\n⏱️  Latency & Rate Limiting")
#     print(f"    Avg generation latency : {avg(agg['gen_latency_ms'])} ms")
#     print(f"    Total elapsed          : {elapsed_min} min")
#     print(f"    RPM budget             : {rate_report['rpm_budget']} req/min")
#     print(f"    Total requests made    : {rate_report['total_requests']}")
#     print(f"    Total time spent waiting  : {rate_report['total_wait_sec']} s")
#     print(f"    Avg wait per request   : {rate_report['avg_wait_per_req']} s")
#     print(f"\n✅  Results saved → {output_path}")
#     print(f"{sep}\n")


# # ══════════════════════════════════════════════════════════════════════════════
# # 11.  CLI
# # ══════════════════════════════════════════════════════════════════════════════

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         description="RAG eval with rate limiting + checkpoints (YOUR rag_service + Groq)")

#     parser.add_argument("--input",      default="/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_filtered_results.json",
#                         help="Path to your retrieval eval JSON file")
#     parser.add_argument("--output",     default="/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/rag_eval_output.json",
#                         help="Output JSON path  (default: rag_eval_output.json)")
#     parser.add_argument("--top_k",      type=int, default=5,
#                         help="top_k for answer_question()  (default: 5)")
#     parser.add_argument("--limit",      type=int, default=50,
#                         help="Evaluate first N questions  (required, e.g. --limit 50)")
#     parser.add_argument("--rpm",        type=int, default=30,
#                         help="Groq requests-per-minute budget  (default: 30)")
#     parser.add_argument("--checkpoint", type=int, default=10,
#                         help="Save progress every N questions  (default: 10)")
#     parser.add_argument("--resume",     action="store_true",
#                         help="Skip questions already saved in --output and continue")

#     args = parser.parse_args()

#     run_pipeline(
#         input_path       = args.input,
#         output_path      = args.output,
#         top_k            = args.top_k,
#         limit            = args.limit,
#         rpm              = args.rpm,
#         checkpoint_every = args.checkpoint,
#         resume           = args.resume,
#     )

"""
RAG Evaluation Pipeline — wired to YOUR system
================================================
Uses your exact:
  - answer_question()  from app/rag_service.py  (retrieval + rerank + Groq generation)
  - No OpenAI, no new retrieval — everything goes through your existing code.

New features:
  - Rate limiter        : stays under Groq's RPM limit (default 30 req/min)
  - Checkpoints         : saves progress every 10 questions → safe to resume
  - Default limit=50    : evaluates first 50 questions out of the box
  - Semantic similarity : separate semantic token PRF + sentence cosine score
  - Date normalization  : reduces false negatives for date-formatted answers
  - Separated latency   : pure gen latency vs API wait time reported distinctly
  - Faithfulness caveat : overlap-based score noted as heuristic in summary

Usage (run from your project root where /app lives):
-----------------------------------------------------
    python rag_eval_pipeline.py --input your_eval_results.json
    python rag_eval_pipeline.py --input your_eval_results.json --rpm 30 --limit 50
    python rag_eval_pipeline.py --input your_eval_results.json --resume   # skip already-done questions

Arguments:
    --input      Path to your retrieval eval JSON  (list of question objects)
    --output     Output JSON path                  (default: rag_eval_output.json)
    --top_k      top_k passed to answer_question   (default: 5)
    --limit      Evaluate first N questions        (default: 50)
    --rpm        Groq requests per minute budget   (default: 30)
    --checkpoint Every N questions save progress   (default: 10)
    --resume     Skip questions already in --output JSON and continue from there
"""

import argparse
import json
import os
import re
import string
import sys
import time
from collections import Counter, deque
from typing import List, Dict, Any, Tuple, Optional

# ── tqdm is optional ──────────────────────────────────────────────────────────
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        total = kwargs.get("total", "?")
        desc  = kwargs.get("desc", "")
        for i, item in enumerate(iterable, 1):
            print(f"\r{desc}: {i}/{total}", end="", flush=True)
            yield item
        print()

# ── sentence-transformers for semantic similarity (optional) ──────────────────
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _SBERT_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False
    print(
        "  ⚠️  sentence-transformers not installed. "
        "Semantic similarity will be skipped.\n"
        "      Install with: pip install sentence-transformers"
    )

# ── Import YOUR rag_service ───────────────────────────────────────────────────
try:
    from app.rag_service import answer_question, IDK_MESSAGE
except ModuleNotFoundError as e:
    sys.exit(
        f"\n[ERROR] Could not import your app: {e}\n"
        "Run this script from your project root directory, e.g.:\n"
        "    python rag_eval_pipeline.py --input data.json\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1.  RATE LIMITER
#     Sliding-window tracker: keeps timestamps of the last `rpm` calls.
#     Before each call it sleeps just long enough to stay under the limit.
# ══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Sliding-window rate limiter for Groq RPM.

    Usage:
        limiter = RateLimiter(rpm=30)
        limiter.wait()          # call before every answer_question()
        limiter.record()        # call right after
    """

    def __init__(self, rpm: int = 30):
        self.rpm         = rpm
        self.window      = 60.0
        self.calls       : deque = deque()
        self._req_count  = 0
        self._wait_total = 0.0

    def wait(self) -> float:
        """Block until it is safe to make the next request. Returns sleep time."""
        now = time.time()
        while self.calls and now - self.calls[0] >= self.window:
            self.calls.popleft()

        if len(self.calls) >= self.rpm:
            sleep_for = self.window - (now - self.calls[0]) + 0.05
            if sleep_for > 0:
                print(f"\n  ⏳  Rate limit: {len(self.calls)}/{self.rpm} req/min — "
                      f"waiting {sleep_for:.1f}s …", flush=True)
                time.sleep(sleep_for)
                self._wait_total += sleep_for
            return sleep_for
        return 0.0

    def record(self):
        """Record that a request was just made."""
        self.calls.append(time.time())
        self._req_count += 1

    def report(self) -> Dict[str, Any]:
        return {
            "total_requests":   self._req_count,
            "total_wait_sec":   round(self._wait_total, 2),
            "avg_wait_per_req": round(self._wait_total / max(self._req_count, 1), 2),
            "rpm_budget":       self.rpm,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 2.  TEXT NORMALISATION  (improved: date normalization + existing rules)
# ══════════════════════════════════════════════════════════════════════════════

# Month name → zero-padded number
_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05",     "june": "06",     "july": "07",  "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}

def normalize_dates(text: str) -> str:
    """
    Collapse common date variants to separate year/month/day tokens so that
    '1776', 'July 4, 1776', and '4 July 1776' all preserve the year token.

    This avoids turning 'July 4, 1776' into one glued token like '17760704'
    after punctuation stripping, which would incorrectly score zero against
    a year-only gold answer such as '1776'.
    """
    # e.g. "July 4, 1776"  ->  "1776 07 04"
    text = re.sub(
        r"\b(" + "|".join(_MONTH_MAP) + r")\s+(\d{1,2}),?\s+(\d{4})\b",
        lambda m: f"{m.group(3)} {_MONTH_MAP[m.group(1).lower()]} {int(m.group(2)):02d}",
        text, flags=re.IGNORECASE,
    )
    # e.g. "4 July 1776"   ->  "1776 07 04"
    text = re.sub(
        r"\b(\d{1,2})\s+(" + "|".join(_MONTH_MAP) + r"),?\s+(\d{4})\b",
        lambda m: f"{m.group(3)} {_MONTH_MAP[m.group(2).lower()]} {int(m.group(1)):02d}",
        text, flags=re.IGNORECASE,
    )
    return text


def normalize(text: str) -> str:
    """
    Full normalisation pipeline:
      1. Date normalisation (collapses 'July 4, 1776' -> '1776 07 04')
      2. Lowercase
      3. Article removal
      4. Punctuation strip
      5. Whitespace collapse
    """
    text = normalize_dates(text)
    text = text.lower()
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def tokenize(text: str) -> List[str]:
    return normalize(text).split()


# ══════════════════════════════════════════════════════════════════════════════
# 3.  GENERATION QUALITY
#     3a. Lexical token-level P / R / F1
#     3b. Optional semantic token-level P / R / F1
#     3c. Sentence-level cosine sim         (stored separately as `semantic_sim`)
# ══════════════════════════════════════════════════════════════════════════════

def token_prf(prediction: str, gold_answers: List[str]) -> Dict[str, float]:
    """
    Lexical token-level Precision, Recall, and F1.

    Example:
      prediction = "July 4, 1776"  -> tokens: ["1776", "07", "04"]
      gold       = "1776"          -> tokens: ["1776"]
      Precision = 1/3 = 33.33, Recall = 1/1 = 100, F1 = 50
    """
    pred_tokens = tokenize(prediction)
    best_p = best_r = best_f1 = 0.0

    for gold in gold_answers:
        gold_tokens = tokenize(gold)
        if not pred_tokens and not gold_tokens:
            p = r = f1 = 1.0
        elif not pred_tokens or not gold_tokens:
            p = r = f1 = 0.0
        else:
            common     = Counter(pred_tokens) & Counter(gold_tokens)
            num_common = sum(common.values())
            p  = num_common / len(pred_tokens)
            r  = num_common / len(gold_tokens)
            f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0

        if f1 > best_f1:
            best_p, best_r, best_f1 = p, r, f1

    return {
        "precision": round(best_p  * 100, 2),
        "recall":    round(best_r  * 100, 2),
        "f1":        round(best_f1 * 100, 2),
    }


def semantic_token_prf(prediction: str,
                       gold_answers: List[str],
                       sim_threshold: float = 0.75) -> Optional[Dict[str, float]]:
    """
    Optional semantic token-level Precision, Recall, and F1.
    Returns None when sentence-transformers is not installed.
    """
    if not _SEMANTIC_AVAILABLE:
        return None

    pred_tokens = tokenize(prediction)
    best_p = best_r = best_f1 = 0.0

    for gold in gold_answers:
        gold_tokens = tokenize(gold)
        if not pred_tokens and not gold_tokens:
            p = r = f1 = 1.0
        elif not pred_tokens or not gold_tokens:
            p = r = f1 = 0.0
        else:
            pred_embs = _SBERT_MODEL.encode(
                pred_tokens, convert_to_tensor=True, show_progress_bar=False
            )
            gold_embs = _SBERT_MODEL.encode(
                gold_tokens, convert_to_tensor=True, show_progress_bar=False
            )
            sim_matrix = st_util.cos_sim(pred_embs, gold_embs)

            gold_claimed = [False] * len(gold_tokens)
            matched = 0

            for i in range(len(pred_tokens)):
                best_j, best_s = -1, 0.0
                for j in range(len(gold_tokens)):
                    if not gold_claimed[j]:
                        s = sim_matrix[i][j].item()
                        if s > best_s:
                            best_s, best_j = s, j
                # Only count the match if it clears the threshold
                if best_j >= 0 and best_s >= sim_threshold:
                    matched += 1
                    gold_claimed[best_j] = True

            p  = matched / len(pred_tokens)
            r  = matched / len(gold_tokens)
            f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0

        if f1 > best_f1:
            best_p, best_r, best_f1 = p, r, f1

    return {
        "precision": round(best_p  * 100, 2),
        "recall":    round(best_r  * 100, 2),
        "f1":        round(best_f1 * 100, 2),
    }


def semantic_similarity(prediction: str, gold_answers: List[str]) -> Optional[float]:
    """
    Embedding cosine similarity between prediction and best-matching gold answer.
    Returns None when sentence-transformers is not installed.

    NOTE: scores are NOT multiplied to a P/R/F1 split here — a single
    max-cosine value is returned and stored as `semantic_sim`.  This is the
    most interpretable number for a generative RAG system and avoids the
    confusion of reporting three "semantic" numbers that users often conflate
    with lexical P/R/F1.
    """
    if not _SEMANTIC_AVAILABLE:
        return None

    pred_emb  = _SBERT_MODEL.encode(prediction,    convert_to_tensor=True)
    gold_embs = _SBERT_MODEL.encode(gold_answers,  convert_to_tensor=True)
    sims      = st_util.cos_sim(pred_emb, gold_embs)[0]
    return round(float(sims.max().item()) * 100, 2)   # 0–100 scale, matches lexical


# ══════════════════════════════════════════════════════════════════════════════
# 4.  ANSWER CORRECTNESS
# ══════════════════════════════════════════════════════════════════════════════

def exact_match(prediction: str, gold_answers: List[str]) -> int:
    pred_norm = normalize(prediction)
    return int(any(normalize(g) == pred_norm for g in gold_answers))


def contains_match(prediction: str, gold_answers: List[str]) -> int:
    pred_norm = normalize(prediction)
    return int(any(normalize(g) in pred_norm for g in gold_answers))


# ══════════════════════════════════════════════════════════════════════════════
# 5.  FAITHFULNESS  (heuristic: word-overlap ≥ 0.3)
#
#     ⚠️  CAVEAT: This is a lexical proxy only. It cannot detect cases where
#     the model retrieves correct context but generates a plausible-sounding
#     wrong answer in different vocabulary.  For production evaluation, spot-
#     check 10–20 examples manually or with an LLM-as-judge pass.
# ══════════════════════════════════════════════════════════════════════════════

def faithfulness_score(answer: str, context: str) -> Tuple[str, float]:
    answer_lc  = answer.lower()
    context_norm = normalize(context)

    if IDK_MESSAGE.lower() in answer_lc or "don't know" in answer_lc:
        return "IDK/FAITHFUL", 1.0

    answer_words = [
        w for w in tokenize(answer)
        if len(w) > 4 or any(ch.isdigit() for ch in w)
    ]
    if not answer_words:
        return "NOT_FAITHFUL", 0.0

    matches = sum(1 for w in answer_words if w in context_norm)
    ratio   = matches / len(answer_words)
    verdict = "FAITHFUL" if ratio >= 0.3 else "NOT_FAITHFUL"
    return verdict, round(ratio, 3)


# ══════════════════════════════════════════════════════════════════════════════
# 6.  CHUNK HELPERS
#     Tuple format: (id, document_id, chunk_text, page_start, page_end, score)
# ══════════════════════════════════════════════════════════════════════════════

def chunks_to_context(chunks: List[Tuple]) -> str:
    return "\n\n".join(
        c[2].strip() for c in chunks if len(c) > 2 and c[2] and c[2].strip()
    )


def avg_chunk_score(chunks: List[Tuple]) -> Optional[float]:
    scores = [c[5] for c in chunks if len(c) > 5]
    return round(sum(scores) / len(scores), 4) if scores else None


# ══════════════════════════════════════════════════════════════════════════════
# 7.  CHECKPOINT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def load_checkpoint(output_path: str) -> Tuple[List[Dict], set]:
    rows: List[Dict] = []
    done_ids: set = set()

    if not os.path.exists(output_path):
        return rows, done_ids

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        for row in rows:
            if row.get("question_id"):
                done_ids.add(row["question_id"])
        print(f"  ↩️  Resumed: found {len(rows)} already-completed questions in {output_path}")
    except Exception as e:
        print(f"  ⚠️  Could not read checkpoint file ({e}), starting fresh.")

    return rows, done_ids


def save_checkpoint(output_path: str, rows: List[Dict], label: str = "") -> None:
    if not rows:
        return
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    tag = f" [{label}]" if label else ""
    print(f"  💾  Checkpoint saved{tag} → {output_path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  CHECKPOINT SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_checkpoint_summary(rows: List[Dict], checkpoint_n: int) -> None:
    def _f(key, cast=float):
        vals = []
        for r in rows:
            v = r.get(key)
            if v not in (None, "", "n/a"):
                try:
                    vals.append(cast(v))
                except (ValueError, TypeError):
                    pass
        return round(sum(vals) / len(vals), 2) if vals else "n/a"

    sep = "-" * 52
    print(f"\n{sep}")
    print(f"  📌  CHECKPOINT  — questions 1–{len(rows)}  (every {checkpoint_n})")
    print(sep)
    print(f"  Lexical Precision  : {_f('gen_precision')}%")
    print(f"  Lexical Recall     : {_f('gen_recall')}%")
    print(f"  Lexical F1         : {_f('gen_f1')}%")
    if _SEMANTIC_AVAILABLE:
        print(f"  Semantic Token F1  : {_f('semantic_token_f1')}%")
        print(f"  Semantic Sim       : {_f('semantic_sim')}%")
    print(f"  Exact Match        : {_f('exact_match')}")
    print(f"  Contains Match     : {_f('contains_match')}")
    print(f"  Faithful rate      : {_f('faithful_binary')}")
    print(f"  Avg RAG latency    : {_f('rag_latency_ms')} ms  (excl. API wait)")
    print(sep + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(input_path:       str,
                 output_path:      str,
                 top_k:            int,
                 limit:            int,
                 rpm:              int,
                 checkpoint_every: int,
                 resume:           bool) -> None:

    # ── Load JSON ─────────────────────────────────────────────────────────────
    with open(input_path, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    if isinstance(data, dict):
        data = next(v for v in data.values() if isinstance(v, list))

    data = data[:limit]

    # ── Resume from checkpoint ────────────────────────────────────────────────
    if resume:
        rows, done_ids = load_checkpoint(output_path)
    else:
        rows, done_ids = [], set()

    # ── Rate limiter ──────────────────────────────────────────────────────────
    limiter = RateLimiter(rpm=rpm)

    # ── Aggregation buckets ───────────────────────────────────────────────────
    agg: Dict[str, list] = {
        "precision":           [],
        "recall":              [],
        "f1":                  [],
        "semantic_token_precision": [],
        "semantic_token_recall":    [],
        "semantic_token_f1":        [],
        "semantic_sim":        [],   # NEW: embedding cosine similarity
        "exact_match":         [],
        "contains_match":      [],
        "faithful":            [],
        "overlap_ratio":       [],
        "num_chunks":          [],
        "avg_chunk_score":     [],
        "rag_latency_ms":      [],   # full answer_question() time, excluding limiter wait
        "api_wait_ms":         [],   # NEW: isolated API wait time
        "total_latency_ms":    [],   # NEW: full end-to-end per question
        "retrieval_hit_at_k":  [],
        "retrieval_mrr":       [],
        "retrieval_latency":   [],
    }

    # Pre-fill agg from resumed rows
    for r in rows:
        def _safe(key, cast=float):
            v = r.get(key)
            try:    return cast(v) if v not in (None, "") else None
            except: return None

        for key in ("gen_precision", "gen_recall", "gen_f1",
                    "semantic_token_precision", "semantic_token_recall",
                    "semantic_token_f1", "semantic_sim",
                    "exact_match", "contains_match",
                    "faithful_binary", "overlap_ratio", "num_chunks_retrieved",
                    "avg_chunk_score", "rag_latency_ms", "pure_gen_latency_ms",
                    "api_wait_ms", "total_latency_ms",
                    "retrieval_hit_at_k", "retrieval_mrr", "retrieval_latency_ms"):
            dest = {
                "gen_precision":         "precision",
                "gen_recall":            "recall",
                "gen_f1":                "f1",
                "faithful_binary":      "faithful",
                "num_chunks_retrieved": "num_chunks",
                "pure_gen_latency_ms":   "rag_latency_ms",
                "retrieval_latency_ms": "retrieval_latency",
            }.get(key, key)
            v = _safe(key)
            if v is not None and dest in agg:
                agg[dest].append(v)

    todo        = [item for item in data if item.get("question_id", "") not in done_ids]
    total_to_do = len(todo)
    skipped     = len(rows)

    print(f"\n🚀  Evaluating {total_to_do} questions  "
          f"(limit={limit}, top_k={top_k}, rpm={rpm}, "
          f"checkpoint every {checkpoint_every})")
    print(f"    Semantic similarity : {'✅ enabled (all-MiniLM-L6-v2)' if _SEMANTIC_AVAILABLE else '⚠️  disabled (pip install sentence-transformers)'}")
    if skipped:
        print(f"    ↩️  Skipping {skipped} already-done questions\n")
    else:
        print()

    eval_start = time.time()

    for idx, item in enumerate(tqdm(todo, desc="Evaluating", total=total_to_do), 1):

        qid      = item.get("question_id", "")
        question = item["question"]
        golds    = item["answers"]

        # ── Rate limit wait (tracked separately from gen latency) ─────────────
        t_wait_start = time.time()
        wait_sec     = limiter.wait()
        api_wait_ms  = round((time.time() - t_wait_start) * 1000, 1)

        # ── Generate answer through the full RAG stack ────────────────────────
        t_rag_start = time.time()
        answer, chunks = answer_question(question, top_k=top_k)
        limiter.record()
        rag_latency_ms = round((time.time() - t_rag_start) * 1000, 1)
        total_lat_ms   = round(api_wait_ms + rag_latency_ms, 1)

        # ── Metrics ───────────────────────────────────────────────────────────
        context      = chunks_to_context(chunks)
        prf          = token_prf(answer, golds)
        sem_prf      = semantic_token_prf(answer, golds)
        sem_sim      = semantic_similarity(answer, golds)       # None if unavailable
        em           = exact_match(answer, golds)
        cm           = contains_match(answer, golds)
        faith, overlap = faithfulness_score(answer, context)
        faithful_bin = 1 if faith in ("FAITHFUL", "IDK/FAITHFUL") else 0
        avg_score    = avg_chunk_score(chunks)

        hit_at_k    = item.get("hit_at_k", item.get("hit_at_1"))
        mrr         = item.get("mrr")
        ret_latency = item.get("latency_ms")

        row = {
            "question_id":       qid,
            "question":          question,
            "gold_answers":      golds,
            "generated_answer":  answer,

            "retrieved_chunks": [
                {
                    "document_id": str(c[1]),
                    "chunk_text":  c[2],
                    "page_start":  c[3],
                    "page_end":    c[4],
                    "score":       c[5],
                }
                for c in chunks
            ],

            # Lexical generation quality
            "gen_precision": prf["precision"],
            "gen_recall":    prf["recall"],
            "gen_f1":        prf["f1"],

            # Semantic generation quality
            "semantic_token_precision": sem_prf["precision"] if sem_prf else None,
            "semantic_token_recall":    sem_prf["recall"] if sem_prf else None,
            "semantic_token_f1":        sem_prf["f1"] if sem_prf else None,
            "semantic_sim":  sem_sim,   # cosine sim 0–100, or null

            # Answer correctness
            "exact_match":    em,
            "contains_match": cm,

            # Faithfulness (heuristic)
            "faithful_verdict":      faith,
            "faithful_binary":       faithful_bin,
            "context_overlap_ratio": overlap,

            # Retrieval
            "num_chunks_retrieved": len(chunks),
            "avg_chunk_score":      avg_score,

            # Separated latency breakdown
            "rag_latency_ms":       rag_latency_ms, # answer_question() excluding limiter wait
            "api_wait_ms":          api_wait_ms,     # time spent waiting on rate limit
            "total_latency_ms":     total_lat_ms,    # sum of both

            # From eval JSON
            "retrieval_hit_at_k":   hit_at_k,
            "retrieval_mrr":        mrr,
            "retrieval_latency_ms": ret_latency,
        }
        rows.append(row)

        # Accumulate
        agg["precision"].append(prf["precision"])
        agg["recall"].append(prf["recall"])
        agg["f1"].append(prf["f1"])
        if sem_prf:
            agg["semantic_token_precision"].append(sem_prf["precision"])
            agg["semantic_token_recall"].append(sem_prf["recall"])
            agg["semantic_token_f1"].append(sem_prf["f1"])
        if sem_sim is not None: agg["semantic_sim"].append(sem_sim)
        agg["exact_match"].append(em)
        agg["contains_match"].append(cm)
        agg["faithful"].append(faithful_bin)
        agg["overlap_ratio"].append(overlap)
        agg["num_chunks"].append(len(chunks))
        agg["rag_latency_ms"].append(rag_latency_ms)
        agg["api_wait_ms"].append(api_wait_ms)
        agg["total_latency_ms"].append(total_lat_ms)
        if avg_score   is not None: agg["avg_chunk_score"].append(avg_score)
        if hit_at_k    is not None: agg["retrieval_hit_at_k"].append(hit_at_k)
        if mrr         is not None: agg["retrieval_mrr"].append(mrr)
        if ret_latency is not None: agg["retrieval_latency"].append(ret_latency)

        # ── Checkpoint ────────────────────────────────────────────────────────
        if idx % checkpoint_every == 0:
            print_checkpoint_summary(rows, checkpoint_every)
            save_checkpoint(output_path, rows,
                            label=f"q{skipped + idx}/{skipped + total_to_do}")

    # ── Final save ────────────────────────────────────────────────────────────
    save_checkpoint(output_path, rows, label="FINAL")

    def avg(lst: list):
        return round(sum(lst) / len(lst), 2) if lst else "n/a"

    elapsed_min = round((time.time() - eval_start) / 60, 2)
    rate_report = limiter.report()
    n           = len(rows)

    FINAL_METRICS_FILE = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/final_rag_metrics.json"

    final_metrics = {
        "generation_quality_lexical": {
            "precision": avg(agg["precision"]),
            "recall":    avg(agg["recall"]),
            "f1":        avg(agg["f1"]),
            "note": (
                "Token-level lexical overlap against gold answers "
                "(normalized: lowercase, articles, punctuation, dates)."
            ),
        },

        "generation_quality_semantic": {
            "token_precision": avg(agg["semantic_token_precision"]) if agg["semantic_token_precision"] else "n/a",
            "token_recall":    avg(agg["semantic_token_recall"]) if agg["semantic_token_recall"] else "n/a",
            "token_f1":        avg(agg["semantic_token_f1"]) if agg["semantic_token_f1"] else "n/a",
            "semantic_sim": avg(agg["semantic_sim"]) if agg["semantic_sim"] else "n/a",
            "model": "all-MiniLM-L6-v2" if _SEMANTIC_AVAILABLE else "not installed",
            "note": (
                "token_* metrics use token-level SBERT matching. semantic_sim is "
                "max sentence-level cosine similarity (0-100) between generated answer "
                "and the best-matching gold answer."
            ),
        },

        "answer_correctness": {
            "exact_match":    avg(agg["exact_match"]),
            "contains_match": avg(agg["contains_match"]),
            "note": (
                "Exact Match measures full-string equality after normalization. "
                "High EM on a filtered NQ subset may reflect easier questions; "
                "compare against full NQ benchmarks (SotA EM ≈ 40–55%) for context."
            ),
        },

        "faithfulness": {
            "faithful_rate": avg(agg["faithful"]),
            "avg_overlap":   avg(agg["overlap_ratio"]),
            "caveat": (
                "⚠️  Faithfulness is measured via word-overlap (threshold ≥ 0.3). "
                "This is a heuristic proxy — it cannot detect vocabulary-shift "
                "hallucinations where the model rephrases context incorrectly. "
                "Recommend a manual or LLM-as-judge spot-check on 10–20 examples."
            ),
        },

        "retrieval_live_system": {
            "avg_chunks_retrieved": avg(agg["num_chunks"]),
            "avg_chunk_score":      avg(agg["avg_chunk_score"]),
        },

        "retrieval_eval_json": {
            "hit_at_k":             avg(agg["retrieval_hit_at_k"]),
            "mrr":                  avg(agg["retrieval_mrr"]),
            "retrieval_latency_ms": avg(agg["retrieval_latency"]),
            "note": (
                "MRR gap vs Hit@K suggests correct chunks are retrieved but "
                "not always ranked first; consider reranker tuning."
            ),
        },

        # Separated latency breakdown  ← NEW
        "latency_breakdown": {
            "avg_rag_latency_ms":      avg(agg["rag_latency_ms"]),
            "avg_api_wait_ms":         avg(agg["api_wait_ms"]),
            "avg_total_latency_ms":    avg(agg["total_latency_ms"]),
            "note": (
                "rag_latency_ms = full answer_question() time excluding rate-limit wait "
                "(embedding, retrieval, reranking, context building, and LLM generation). "
                "api_wait_ms = time blocked by RPM rate limiter.  "
                "For pure LLM latency, instrument app.llm.generate_answer directly."
            ),
        },

        "rate_limit_info": {
            "rpm_budget":              rate_report["rpm_budget"],
            "total_requests":          rate_report["total_requests"],
            "total_wait_sec":          rate_report["total_wait_sec"],
            "avg_wait_per_request_sec": rate_report["avg_wait_per_req"],
            "total_elapsed_min":       elapsed_min,
        },

        "evaluation_info": {
            "num_questions": n,
            "top_k":         top_k,
        },
    }

    with open(FINAL_METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=4)

    print(f"\n📁 Final metrics saved → {FINAL_METRICS_FILE}")

    # ══════════════════════════════════════════════════════════════════════════
    # 10.  FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  RAG EVALUATION SUMMARY  (n={n} questions, top_k={top_k})")
    print(sep)

    print("\n📊  Generation Quality — Lexical  (token-level, paper-style)")
    print(f"    Precision : {avg(agg['precision'])}%")
    print(f"    Recall    : {avg(agg['recall'])}%")
    print(f"    F1        : {avg(agg['f1'])}%")

    if agg["semantic_sim"]:
        print("\n🧠  Generation Quality — Semantic  (embedding cosine, all-MiniLM-L6-v2)")
        print(f"    Token Precision     : {avg(agg['semantic_token_precision'])}%")
        print(f"    Token Recall        : {avg(agg['semantic_token_recall'])}%")
        print(f"    Token F1            : {avg(agg['semantic_token_f1'])}%")
        print(f"    Semantic Similarity : {avg(agg['semantic_sim'])}%")
        print(f"    (captures correct answers that use vocabulary different from gold)")
    else:
        print("\n🧠  Generation Quality — Semantic : ⚠️  skipped (sentence-transformers not installed)")

    print("\n✅  Answer Correctness")
    print(f"    Exact Match    : {avg(agg['exact_match'])}")
    print(f"    Contains Match : {avg(agg['contains_match'])}")
    print(f"    Note: EM is evaluated on a filtered NQ subset; full NQ SotA EM ≈ 40–55%.")

    print("\n🔍  Faithfulness  (heuristic: context word-overlap ≥ 0.3)")
    print(f"    Faithful rate  : {avg(agg['faithful'])}")
    print(f"    Avg overlap    : {avg(agg['overlap_ratio'])}")
    print(f"    ⚠️  Caveat: word-overlap cannot catch vocabulary-shift hallucinations.")
    print(f"    Recommend a manual or LLM-as-judge spot-check on 10–20 examples.")

    print("\n📥  Retrieval  (live system)")
    print(f"    Avg chunks retrieved : {avg(agg['num_chunks'])}")
    print(f"    Avg chunk score      : {avg(agg['avg_chunk_score'])}")

    if agg["retrieval_hit_at_k"]:
        print("\n📥  Retrieval  (from eval JSON)")
        print(f"    Hit@K             : {avg(agg['retrieval_hit_at_k'])}")
        print(f"    MRR               : {avg(agg['retrieval_mrr'])}")
        print(f"    Retrieval latency : {avg(agg['retrieval_latency'])} ms")
        print(f"    Note: MRR < Hit@K → correct chunk retrieved but not always ranked #1.")

    print("\n⏱️  Latency — separated breakdown")
    print(f"    Avg RAG latency      : {avg(agg['rag_latency_ms'])} ms")
    print(f"    Avg API wait         : {avg(agg['api_wait_ms'])} ms")
    print(f"    Avg total per query  : {avg(agg['total_latency_ms'])} ms")
    print(f"    Total elapsed        : {elapsed_min} min")

    print("\n🔧  Rate Limit Stats")
    print(f"    RPM budget             : {rate_report['rpm_budget']} req/min")
    print(f"    Total requests made    : {rate_report['total_requests']}")
    print(f"    Total time waiting     : {rate_report['total_wait_sec']} s")
    print(f"    Avg wait per request   : {rate_report['avg_wait_per_req']} s")

    print(f"\n✅  Results saved → {output_path}")
    print(f"{sep}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 11.  CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RAG eval with rate limiting + checkpoints (YOUR rag_service + Groq)")

    parser.add_argument("--input",
                        default="/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_filtered_results.json",
                        help="Path to your retrieval eval JSON file")
    parser.add_argument("--output",
                        default="/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/rag_eval_output.json",
                        help="Output JSON path  (default: rag_eval_output.json)")
    parser.add_argument("--top_k",      type=int, default=5,
                        help="top_k for answer_question()  (default: 5)")
    parser.add_argument("--limit",      type=int, default=50,
                        help="Evaluate first N questions  (default: 50)")
    parser.add_argument("--rpm",        type=int, default=30,
                        help="Groq requests-per-minute budget  (default: 30)")
    parser.add_argument("--checkpoint", type=int, default=10,
                        help="Save progress every N questions  (default: 10)")
    parser.add_argument("--resume",     action="store_true",
                        help="Skip questions already saved in --output and continue")

    args = parser.parse_args()

    run_pipeline(
        input_path       = args.input,
        output_path      = args.output,
        top_k            = args.top_k,
        limit            = args.limit,
        rpm              = args.rpm,
        checkpoint_every = args.checkpoint,
        resume           = args.resume,
    )
