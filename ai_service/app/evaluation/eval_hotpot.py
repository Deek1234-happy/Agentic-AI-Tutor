"""
HotpotQA — Retrieval Evaluation
=================================
بيقيس جودة الـ retrieval على 500 سؤال HotpotQA

Metrics (Han et al. §4.1):
  - Precision@K  : من الـ chunks اللي رجعت، كام واحد gold؟
  - Recall@K     : من الـ gold chunks، كام واحد اترجع؟
  - F1@K         : harmonic mean of P & R

Gold label = source_title بتاع الـ chunk مطابق لـ gold_chunks في الـ eval file
(يعني الـ 2 Wikipedia titles اللي بيحتوي عليهم الـ answer)

Run:
  python -m app.evaluation.eval_hotpot_retrieval
"""

import json
import time
import requests
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

SEARCH_URL = "http://localhost:8000/search/"
EVAL_FILE  = "data/hotpot_eval.json"
RESULTS_FILE = "data/hotpot_retrieval_results.json"

TOP_K_VALUES = [5, 10]      # نقيس عند كل قيمة
MAIN_K       = 5            # الـ K الرئيسي في الـ summary


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(retrieved_titles: list[str], gold_titles: list[str]) -> dict:
    """
    retrieved_titles : source_title من كل chunk رجعت
    gold_titles      : العناوين الـ gold (عادةً 2 في HotpotQA)
    """
    gold_set      = set(gold_titles)
    retrieved_set = set(retrieved_titles)

    tp        = len(gold_set & retrieved_set)
    precision = tp / len(retrieved_set) if retrieved_set else 0.0
    recall    = tp / len(gold_set)      if gold_set      else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp}


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluation loop
# ─────────────────────────────────────────────────────────────────────────────

def evaluate():
    # ── Load eval questions ───────────────────────────────────────────────
    if not Path(EVAL_FILE).exists():
        print(f"❌ {EVAL_FILE} مش موجود!")
        print("شغّل الأول: python -m app.evaluation.hotpot_download")
        return

    with open(EVAL_FILE) as f:
        questions = json.load(f)

    print("=" * 60)
    print("HotpotQA — Retrieval Evaluation")
    print(f"Questions : {len(questions)}")
    print(f"K values  : {TOP_K_VALUES}")
    print(f"Endpoint  : {SEARCH_URL}")
    print("=" * 60)

    # ── Accumulators per K ────────────────────────────────────────────────
    # scores[k] = list of metric dicts
    scores     = {k: [] for k in TOP_K_VALUES}
    # breakdown by hotpot_type (bridge / comparison)
    by_type    = {k: defaultdict(list) for k in TOP_K_VALUES}

    errors     = 0
    t_start    = time.time()

    for i, q in enumerate(questions):
        question    = q["question"]
        gold_titles = q["gold_chunks"]   # list of 2 Wikipedia titles
        qtype       = q.get("hotpot_type", "unknown")

        # ── Call search endpoint once per question (max K) ────────────────
        max_k = max(TOP_K_VALUES)
        try:
            resp = requests.post(
                SEARCH_URL,
                json={
                    "query":   question,
                    "top_k":   max_k,
                    "user_id": "97449496-0bdf-4169-8e82-73388cacafbd",          # evaluation mode — no user filter
                },
                timeout=120,
            )
            resp.raise_for_status()
            results = resp.json()             # List[SearchResponse]

        except Exception as e:
            errors += 1
            print(f"  ❌ Q{i}: {e}")
            # fill zeros for all K
            for k in TOP_K_VALUES:
                scores[k].append({"precision": 0, "recall": 0, "f1": 0, "tp": 0})
                by_type[k][qtype].append({"precision": 0, "recall": 0, "f1": 0})
            continue

        # ── Compute metrics for each K ────────────────────────────────────
        for k in TOP_K_VALUES:
            top_k_results    = results[:k]
            retrieved_titles = [r["source_title"] for r in top_k_results]
            m = compute_metrics(retrieved_titles, gold_titles)
            scores[k].append(m)
            by_type[k][qtype].append(m)

        if (i + 1) % 100 == 0:
            elapsed = time.time() - t_start

            avg_p = sum(s["precision"] for s in scores[MAIN_K]) / len(scores[MAIN_K])
            avg_r = sum(s["recall"]    for s in scores[MAIN_K]) / len(scores[MAIN_K])
            avg_f1 = sum(s["f1"]       for s in scores[MAIN_K]) / len(scores[MAIN_K])

            print(f"  [{i+1}/{len(questions)}]  "
                f"P@{MAIN_K}={avg_p:.3f}  "
                f"R@{MAIN_K}={avg_r:.3f}  "
                f"F1@{MAIN_K}={avg_f1:.3f}  "
                f"errors={errors}  elapsed={elapsed:.0f}s")

    # ─────────────────────────────────────────────────────────────────────
    # Aggregate results
    # ─────────────────────────────────────────────────────────────────────

    def avg(lst, key):
        return sum(x[key] for x in lst) / len(lst) if lst else 0.0

    summary = {}
    for k in TOP_K_VALUES:
        s = scores[k]
        summary[f"@{k}"] = {
            "precision": round(avg(s, "precision"), 4),
            "recall":    round(avg(s, "recall"),    4),
            "f1":        round(avg(s, "f1"),        4),
            "by_type": {
                qtype: {
                    "precision": round(avg(ms, "precision"), 4),
                    "recall":    round(avg(ms, "recall"),    4),
                    "f1":        round(avg(ms, "f1"),        4),
                    "count":     len(ms),
                }
                for qtype, ms in by_type[k].items()
            }
        }

    total_time = time.time() - t_start
    output = {
        "dataset":      "HotpotQA",
        "n_questions":  len(questions),
        "errors":       errors,
        "total_time_s": round(total_time, 1),
        "results":      summary,
    }

    # ─────────────────────────────────────────────────────────────────────
    # Print summary
    # ─────────────────────────────────────────────────────────────────────

    print(f"\n{'='*60}")
    print(f"HotpotQA Retrieval Results  ({len(questions)} questions)")
    print(f"{'='*60}")
    print(f"{'K':<6} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print(f"{'-'*40}")
    for k in TOP_K_VALUES:
        r = summary[f"@{k}"]
        print(f"@{k:<5} {r['precision']:>10.4f} {r['recall']:>10.4f} {r['f1']:>10.4f}")

    print(f"\n── By Type (@{MAIN_K}) ──────────────────────────")
    r_main = summary[f"@{MAIN_K}"]["by_type"]
    print(f"{'Type':<15} {'Precision':>10} {'Recall':>10} {'F1':>10} {'N':>6}")
    print(f"{'-'*50}")
    for qtype, m in sorted(r_main.items()):
        print(f"{qtype:<15} {m['precision']:>10.4f} {m['recall']:>10.4f} "
              f"{m['f1']:>10.4f} {m['count']:>6}")

    print(f"\nErrors   : {errors}/{len(questions)}")
    print(f"Time     : {total_time:.1f}s  ({total_time/len(questions):.2f}s/q)")

    # ─────────────────────────────────────────────────────────────────────
    # Save results
    # ─────────────────────────────────────────────────────────────────────

    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Results saved → {RESULTS_FILE}")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    evaluate()