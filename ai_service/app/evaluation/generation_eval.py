import json
import re
import string
from collections import Counter
import numpy as np

from app.llm import generate_answer

# ============================================
# CONFIG
# ============================================

DATASET_FILE   = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_eval.json"
RETRIEVAL_FILE = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/filtered_data.json"

TOP_K = 5

# ============================================
# NORMALIZATION
# ============================================

def normalize(text):
    text = text.lower()
    text = re.sub(f"[{string.punctuation}]", "", text)
    return text.split()

def compute_f1(pred, truth):
    pred_tokens = normalize(pred)
    truth_tokens = normalize(truth)

    common = Counter(pred_tokens) & Counter(truth_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0, 0, 0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(truth_tokens)
    f1 = 2 * precision * recall / (precision + recall)

    return precision, recall, f1

def compute_f1_multi(pred, gold_answers):
    scores = []
    for truth in gold_answers:
        scores.append(compute_f1(pred, truth))
    return max(scores, key=lambda x: x[2])

def compute_em(pred, gold_answers):
    pred_norm = " ".join(normalize(pred))
    for truth in gold_answers:
        if pred_norm == " ".join(normalize(truth)):
            return 1
    return 0

# ============================================
# GENERATION
# ============================================

def generate_from_context(question, contexts):

    contexts = contexts[:TOP_K]

    context_text = "\n".join(contexts)

    prompt = f"""
Extract the exact answer from the context.
Return ONLY the answer (few words).

If the answer is not in the context, say:
"I don't know"

CONTEXT:
{context_text}

QUESTION:
{question}

ANSWER:
"""

    try:
        answer = generate_answer(prompt, temperature=0)
        answer = answer.strip() if answer else "I don't know"
    except Exception:
        answer = "I don't know"

    answer = answer.split("\n")[0]
    answer = answer.split(".")[0]

    return answer

# ============================================
# MAIN EVALUATION
# ============================================

def run_evaluation(limit=100):

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    with open(RETRIEVAL_FILE, "r", encoding="utf-8") as f:
        retrieval_data = json.load(f)

    # 🔥 mapping الصحيح
    retrieval_map = {
        item["question_id"]: item
        for item in retrieval_data
    }

    results = []

    for i in range(limit):

        question = dataset[i]["question"]
        gold_answers = dataset[i]["gold_answers"]
        qid = dataset[i]["id"]   # من dataset

        if qid not in retrieval_map:
            print(f"⚠️ Missing retrieval for: {qid}")
            continue

        contexts = retrieval_map[qid]["retrieved_texts"]

        # debug لأول 3
        if i < 3:
            print("\nDEBUG")
            print("Q:", question)
            print("Context sample:", contexts[0][:200])

        pred = generate_from_context(question, contexts)

        p, r, f1 = compute_f1_multi(pred, gold_answers)
        em = compute_em(pred, gold_answers)

        results.append({
            "precision": p,
            "recall": r,
            "f1": f1,
            "em": em
        })

        if f1 < 0.3:
            print("\n❌ BAD CASE")
            print("Q:", question)
            print("Pred:", pred)
            print("GT:", gold_answers)

        print(f"{i} done")

    # ============================================
    # FINAL RESULTS
    # ============================================

    avg_p = np.mean([x["precision"] for x in results])
    avg_r = np.mean([x["recall"] for x in results])
    avg_f = np.mean([x["f1"] for x in results])
    avg_em = np.mean([x["em"] for x in results])

    print("\n===== FINAL RESULTS =====")
    print("Precision:", round(avg_p, 4))
    print("Recall:", round(avg_r, 4))
    print("F1:", round(avg_f, 4))
    print("EM:", round(avg_em, 4))


# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    run_evaluation(limit=100)