from datasets import load_dataset
from .evaluation_service import evaluate
# from .ragas_eval import evaluate_ragas, ragas_llm, ragas_embeddings, faithfulness, answer_relevancy, context_precision, context_recall

import numpy as np
import json
import time
import re
from collections import Counter
import uuid
from datetime import datetime


# =========================
# 1. CONFIG
# =========================
DATASET_NAME = "hotpot_qa"
SPLIT        = "validation[:10]"
SAVE_PATH    = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


# =========================
# 2. TEXT NORMALIZATION
# =========================
def normalize(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


# =========================
# 3. METRICS (F1 / P / R)
# =========================
def compute_f1_precision_recall(pred, truth):
    pred_tokens  = normalize(pred).split()
    truth_tokens = normalize(truth).split()

    common   = Counter(pred_tokens) & Counter(truth_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0.0, 0.0, 0.0

    precision = num_same / len(pred_tokens)  if pred_tokens  else 0.0
    recall    = num_same / len(truth_tokens) if truth_tokens else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return f1, precision, recall


# =========================
# 4. PAYLOAD BUILDER
# =========================
def build_payload(example, i):
    return {
        "question":             example["question"],
        "session_id":           str(uuid.uuid4()),
        "user_id":              "97470af6-ee7d-4615-be3b-8825379395e3",
        "subject_id":           "dc67f1da-25a2-4e00-8f31-81caffc27418",
        "allowed_document_ids": None,
        "top_k":                5,
    }


# =========================
# 5. SAFE AVG
# =========================
def safe_avg(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return float(np.mean(values)) if values else 0.0


def avg_judge(results, model, metric):
    vals = [
        r.get("judge", {}).get(model, {}).get(metric)
        for r in results
        if isinstance(r.get("judge", {}).get(model), dict)
    ]
    return safe_avg(vals)


def avg_extra(results, model, metric):
    return safe_avg([
        r.get("extra_metrics", {}).get(model, {}).get(metric)
        for r in results
    ])


# ── RAGAS avg helper (disabled — re-enable when token limit allows) ──
# def avg(results, model, metric):
#     return safe_avg([r["ragas"][model].get(metric) for r in results])


# =========================
# 6. MAIN RUN
# =========================
def run():
    dataset = load_dataset(DATASET_NAME, "distractor", split=SPLIT)

    results    = []
    failed     = 0
    start_time = time.time()

    for i, example in enumerate(dataset):
        try:
            print(f"\n🔹 Q{i}: {example['question']}")
            payload = build_payload(example, i)

            # RAGAS disabled → mode="judge" only
            result = evaluate(
                payload,
                ground_truth=example["answer"],
                mode="judge",
            )

            # ── Extra metrics (F1 / P / R) ────────────────
            gt = example["answer"]
            for model_key in ("llm", "rag", "kg_rag"):
                ans      = result["answers"][model_key]
                f1, p, r = compute_f1_precision_recall(ans, gt)
                result.setdefault("extra_metrics", {})[model_key] = {
                    "f1": f1, "precision": p, "recall": r,
                }

            results.append(result)
            print(f"✅ Done {i}")
            time.sleep(3)

        except Exception as e:
            print(f"❌ Error at {i}: {e}")
            failed += 1
            continue

    # ── Save ──────────────────────────────────────────────
    with open(SAVE_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {SAVE_PATH}")

    # ── Judge summary ─────────────────────────────────────
    judge_metrics = [
        "correctness", "relevance", "faithfulness",
        "groundedness", "completeness", "reasoning",
    ]

    print("\n=========================")
    print("JUDGE SCORES (avg over all questions)")
    print("=========================")

    model_overall = {}
    for model in ["LLM", "RAG", "KG+RAG"]:
        print(f"\n🔹 {model}")
        scores = {}
        for m in judge_metrics:
            val      = avg_judge(results, model, m)
            scores[m] = val
            print(f"  {m}: {val:.4f}")
        overall          = safe_avg(list(scores.values()))
        model_overall[model] = overall
        print(f"  ── OVERALL: {overall:.4f}")

    # ── Best model ────────────────────────────────────────
    print("\n=========================")
    print("BEST MODEL")
    print("=========================")
    for model, score in model_overall.items():
        print(f"  {model}: {score:.4f}")
    best = max(model_overall, key=model_overall.get)
    print(f"\n  🏆 Best: {best} ({model_overall[best]:.4f})")

    # ── Extra metrics summary ─────────────────────────────
    print("\n=========================")
    print("EXTRA METRICS (avg over all questions)")
    print("=========================")
    for model in ["llm", "rag", "kg_rag"]:
        print(f"\n🔹 {model.upper()}")
        for m in ["f1", "precision", "recall"]:
            print(f"  {m}: {avg_extra(results, model, m):.4f}")

    # ── Stats ─────────────────────────────────────────────
    total_time = time.time() - start_time
    print("\n=========================")
    print("STATS")
    print("=========================")
    print(f"Total samples : {len(dataset)}")
    print(f"Success       : {len(results)}")
    print(f"Failed        : {failed}")
    print(f"Time          : {total_time:.2f}s")
    print(f"Avg/sample    : {total_time / max(len(results), 1):.2f}s")

    # ── RAGAS (disabled) ──────────────────────────────────
    # ragas_metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    # for model in ["llm", "rag", "kg_rag"]:
    #     print(f"\n🔹 {model.upper()} (RAGAS)")
    #     for m in ragas_metrics:
    #         print(f"  {m}: {avg(results, model, m):.4f}")


# =========================
# 7. RUN
# =========================
if __name__ == "__main__":
    run()