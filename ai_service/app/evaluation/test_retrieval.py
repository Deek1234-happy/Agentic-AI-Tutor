import json
import requests
import re

SEARCH_URL = "http://localhost:8000/search/"
DATA_FILE = "data/hotpot_eval.json"

TOP_K = 20


# ─────────────────────────────
# Normalize function (مهم جدًا)
# ─────────────────────────────
def normalize(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)        # remove extra spaces
    text = re.sub(r"[^\w\s]", "", text)     # remove punctuation
    return text.strip()


# ─────────────────────────────
# Evaluation
# ─────────────────────────────
def evaluate():
    with open(DATA_FILE) as f:
        data = json.load(f)

    found = 0
    total = len(data)

    for i, item in enumerate(data):
        q = item["question"]

        # ✅ fix answers field
        answers = item.get("gold_answers") or [item.get("gold_answer", "")]

        resp = requests.post(
            SEARCH_URL,
            json={
                "query": q,
                "top_k": TOP_K,
                "user_id": "c6d407cd-a0c6-474e-b5bb-0fd475935b31",
            }
        )

        results = resp.json()

        texts = [r["text"] for r in results]

        # ✅ normalized matching
        hit = any(
            any(normalize(ans) in normalize(t) for ans in answers)
            for t in texts
        )

        if hit:
            found += 1

        if (i + 1) % 50 == 0:
            print(f"[{i+1}/{total}] Recall@20 = {found/(i+1):.3f}")

    print("\nFinal Recall@20:", found / total)


if __name__ == "__main__":
    evaluate()