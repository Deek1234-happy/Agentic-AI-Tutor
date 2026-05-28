"""
HotpotQA — Preparation (UPDATED VERSION)
========================================

✔ الهدف:
- 1000 bridge questions فقط
- كل paragraph = document مستقل
- حفظ documents في folder
- حفظ questions في JSON
- بدون DB (جاهز للـ RAG pipeline)

Run:
  python prepare_hotpot.py
"""

import os
import json
from tqdm import tqdm
from datasets import load_dataset

# =========================
# CONFIG
# =========================
TARGET = 1000
SHUFFLE_BUFFER = 2000

OUTPUT_DIR = "data/hotpot_corpus"
QUESTIONS_FILE = "data/hotpot_questions.json"

os.makedirs("data", exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# MAIN FUNCTION
# =========================

def prepare_hotpot():
    print("=" * 60)
    print("HotpotQA — Preparation (FINAL VERSION)")
    print(f"Target: {TARGET} bridge questions")
    print("=" * 60)

    # Load dataset (streaming)
    stream = load_dataset(
        "hotpot_qa", "distractor",
        split="validation",
        streaming=True,
    )
    stream = stream.shuffle(seed=42, buffer_size=SHUFFLE_BUFFER)

    questions = []
    seen_texts = set()
    doc_id = 0

    for record in stream:

        # ✅ filter bridge only
        if record["type"] != "bridge":
            continue

        question = record["question"]
        answer   = record["answer"]

        # gold titles (supporting facts)
        gold_titles = list(set(record["supporting_facts"]["title"]))

        # ─────────────────────────────
        # SAVE DOCUMENTS (PARAGRAPHS)
        # ─────────────────────────────
        for title, sents in zip(
            record["context"]["title"],
            record["context"]["sentences"]
        ):
            paragraph = " ".join(sents).strip()

            if not paragraph:
                continue

            # remove duplicates
            if paragraph in seen_texts:
                continue
            seen_texts.add(paragraph)

            file_path = os.path.join(
                OUTPUT_DIR,
                f"doc_{doc_id:06d}.txt"
            )

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\nText: {paragraph}")

            doc_id += 1

        # ─────────────────────────────
        # SAVE QUESTION
        # ─────────────────────────────
        questions.append({
            "id": f"HOTPOT-{str(len(questions)).zfill(4)}",
            "question": question,
            "answer": answer,
            "supporting_facts": record["supporting_facts"],
            "gold_titles": gold_titles,
            "dataset": "HotpotQA",
            "type": record["type"],
            "level": record["level"]
        })

        if len(questions) % 100 == 0:
            print(f"Collected {len(questions)}/{TARGET} questions")

        if len(questions) >= TARGET:
            break

    # =========================
    # SAVE QUESTIONS FILE
    # =========================
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("✅ DONE")
    print(f"📁 Documents folder: {OUTPUT_DIR} ({doc_id} docs)")
    print(f"📄 Questions file: {QUESTIONS_FILE} ({len(questions)} questions)")
    print("=" * 60)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    prepare_hotpot()