"""
Phase 1 — Retrieval Evaluation (NQ)
=====================================
Han et al. (2026) §3: "decouple retrieval from generation"

What this file does:
  - Calls /search/ for each NQ question
  - Saves retrieved chunks + titles + scores
  - Reports retrieval accuracy = Hit@K (answer string in context)
    → matches Han et al. Appendix C / Table 16

What this file does NOT do:
  - Generation  (that is Phase 2 — eval_nq_generation.py)
  - P/R/F1 on generated answers (that is Phase 2)

Output:
  data/nq_retrieval_results.json   ← input for Phase 2
  data/nq_retrieval_metrics.json   ← retrieval-only metrics
"""

import json
import re
import time
import os
import requests
import random

os.makedirs("data", exist_ok=True)

BASE_URL   = "http://localhost:8000"
SEARCH_URL = f"{BASE_URL}/search/"

NQ_USER_ID = "576c84a0-b336-4c65-a0c2-6a43c2dbc420"

QUESTIONS_FILE         = "data/nq_eval_1000.json"
RETRIEVAL_RESULTS_FILE = "data/nq_retrieval_results.json"
METRICS_FILE           = "data/nq_retrieval_metrics.json"

K = 10   # Han et al. §3.4 — k=10 by default
CHECKPOINT_EVERY = 10
RUN_SANITY_CHECK = False


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """
    Improved normalization:
    - lowercase
    - fix spacing around punctuation
    - remove punctuation (except numbers/letters)
    - normalize spaces
    """
    text = text.lower()

    # fix spacing around commas
    text = re.sub(r"\s*,\s*", ", ", text)

    # remove punctuation
    text = re.sub(r"[^a-z0-9, ]", " ", text)

    # normalize spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def chunk_contains_answer(chunk_text: str, gold_answers: list) -> bool:
    """
    Robust answer matching
    """
    norm_chunk = normalize_text(chunk_text)

    for ans in gold_answers:
        norm_ans = normalize_text(ans)

        if norm_ans in norm_chunk:
            return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# RETRIEVAL METRICS
# ─────────────────────────────────────────────────────────────────────────────

def retrieval_metrics(retrieved_texts: list, gold_answers: list, k: int = K):

    retrieved_k = retrieved_texts[:k]

    # Hit@K
    hit_at_k = int(any(
        chunk_contains_answer(t, gold_answers)
        for t in retrieved_k
    ))

    # Hit@1
    hit_at_1 = int(
        bool(retrieved_k)
        and chunk_contains_answer(retrieved_k[0], gold_answers)
    )

    # MRR
    mrr = 0.0

    for rank, chunk in enumerate(retrieved_k, 1):
        if chunk_contains_answer(chunk, gold_answers):
            mrr = 1.0 / rank
            break

    return {
        "hit_at_k": hit_at_k,
        "hit_at_1": hit_at_1,
        "mrr": round(mrr, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# RETRIEVAL CALL
# ─────────────────────────────────────────────────────────────────────────────

def call_retrieval(question: str, top_k: int = K):

    response = requests.post(
        SEARCH_URL,
        json={
            "query": question,
            "top_k": top_k,
            "user_id": NQ_USER_ID,
            "allowed_document_ids": None,
        },
        timeout=200,
    )

    response.raise_for_status()

    results = response.json()

    chunk_texts = [r["text"] for r in results]
    chunk_titles = [r["source_title"] for r in results]
    scores = [r["score"] for r in results]
    rerank_scores = [r.get("rerank_score") for r in results]
    final_scores = [r.get("final_score") for r in results]

    return chunk_texts, chunk_titles, scores, rerank_scores, final_scores


def save_json_atomic(path: str, payload):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, path)


def save_checkpoint(results: list):
    save_json_atomic(RETRIEVAL_RESULTS_FILE, results)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_retrieval_evaluation():

    print("=" * 62)
    print("Phase 1 — Retrieval Evaluation (NQ)")
    print(f"Endpoint : {SEARCH_URL}")
    print(f"User ID  : {NQ_USER_ID}")
    print(f"K        : {K}")
    print("=" * 62)

    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)

        # optional sampling
        # random.seed(42)
        # questions = random.sample(questions, 100)

        # first 300 only
        # questions = questions[:300]

    print(f"Loaded {len(questions)} questions\n")

    # ────────────────────────────────────────────────────────────────────────
    # RESUME SUPPORT
    # ────────────────────────────────────────────────────────────────────────

    results = []
    failed = []
    total_time = 0

    if os.path.exists(RETRIEVAL_RESULTS_FILE):

        with open(RETRIEVAL_RESULTS_FILE, "r") as f:
            results = json.load(f)

        print(f"💾 Loaded checkpoint: {len(results)} results")

    if RUN_SANITY_CHECK and not results:

        print("── Sanity check (first question) ──────────────────────────")

        q0 = questions[0]

        print(f"Question     : {q0['question']}")
        print(f"answers      : {q0['answers']}")

        try:
            texts, titles, scores, rerank_scores, final_scores = call_retrieval(
                q0["question"],
                top_k=3
            )

            print(f"Retrieved    : {len(texts)} chunks")
            print(f"Scores       : {[round(s, 3) for s in scores]}")
            print(f"Top chunk    : {texts[0][:120] if texts else 'EMPTY'}")

            hit = any(
                chunk_contains_answer(t, q0["answers"])
                for t in texts
            )

            print(f"Answer found : {'✅ YES' if hit else '❌ NO'}")

        except Exception as e:
            print(f"⚠️ FAILED: {e}")
            return

        print("───────────────────────────────────────────────────────────\n")

    processed_ids = {
        r["question_id"]
        for r in results
    }

    failed = [
        r["question_id"]
        for r in results
        if "error" in r
    ]

    total_time = sum(
        r.get("latency_ms", 0)
        for r in results
    )

    # ────────────────────────────────────────────────────────────────────────
    # FULL LOOP
    # ────────────────────────────────────────────────────────────────────────

    for i, q in enumerate(questions):

        # skip processed questions
        if q["id"] in processed_ids:
            continue

        t_start = time.time()

        try:

            chunk_texts, chunk_titles, scores, rerank_scores, final_scores = call_retrieval(
                q["question"],
                top_k=K
            )

            latency_ms = int((time.time() - t_start) * 1000)

            total_time += latency_ms

            metrics = retrieval_metrics(
                chunk_texts,
                q["answers"],
                k=K
            )

            results.append({

                # gold
                "question_id": q["id"],
                "question": q["question"],
                "answers": q["answers"],
                "doc_title": q["doc_title"],

                # retrieved
                "retrieved_texts": chunk_texts,
                "retrieved_titles": chunk_titles,
                "retrieval_scores": scores,
                "rerank_scores": rerank_scores,
                "final_scores": final_scores,

                # metrics
                "hit_at_k": metrics["hit_at_k"],
                "hit_at_1": metrics["hit_at_1"],
                "mrr": metrics["mrr"],

                "latency_ms": latency_ms,
            })

        except Exception as e:

            failed.append(q["id"])

            results.append({

                "question_id": q["id"],
                "question": q["question"],
                "answers": q["answers"],
                "doc_title": q["doc_title"],

                "retrieved_texts": [],
                "retrieved_titles": [],
                "retrieval_scores": [],
                "rerank_scores": [],
                "final_scores": [],

                "hit_at_k": 0,
                "hit_at_1": 0,
                "mrr": 0.0,

                "latency_ms": 0,
                "error": str(e),
            })

        # ── Save checkpoint frequently so crashes can resume ───────────────

        if len(results) % CHECKPOINT_EVERY == 0:

            save_checkpoint(results)

            print(f"💾 Checkpoint saved ({len(results)} results)")

        # ── Progress logging every 100 ─────────────────────────────────────

        if len(results) % 100 == 0:

            valid = [
                r for r in results
                if "error" not in r
            ]

            avg_hitk = (
                sum(r["hit_at_k"] for r in valid) / len(valid)
                if valid else 0
            )

            avg_hit1 = (
                sum(r["hit_at_1"] for r in valid) / len(valid)
                if valid else 0
            )

            avg_mrr = (
                sum(r["mrr"] for r in valid) / len(valid)
                if valid else 0
            )

            print(
                f"[{len(results)}/{len(questions)}]  "
                f"Hit@{K}={avg_hitk*100:.1f}%  "
                f"Hit@1={avg_hit1*100:.1f}%  "
                f"MRR={avg_mrr*100:.1f}%  "
                f"failed={len(failed)}"
            )

    # ────────────────────────────────────────────────────────────────────────
    # FINAL SAVE
    # ────────────────────────────────────────────────────────────────────────

    save_checkpoint(results)

    valid = [
        r for r in results
        if "error" not in r
    ]

    def avg(field):

        return round(
            100 * sum(r[field] for r in valid) / len(valid),
            2
        ) if valid else 0.0

    metrics_summary = {

        "Hit@K": avg("hit_at_k"),
        "Hit@1": avg("hit_at_1"),
        "MRR": avg("mrr"),

        "K": K,

        "n_questions": len(questions),
        "n_valid": len(valid),
        "n_failed": len(failed),

        "avg_latency_ms": round(
            total_time / len(questions),
            1
        ) if questions else 0,
    }

    save_json_atomic(METRICS_FILE, metrics_summary)

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    print(f"Hit@{K} : {metrics_summary['Hit@K']}%")
    print(f"Hit@1   : {metrics_summary['Hit@1']}%")
    print(f"MRR     : {metrics_summary['MRR']}%")

    print("=" * 50)

    return metrics_summary


if __name__ == "__main__":
    run_retrieval_evaluation()
