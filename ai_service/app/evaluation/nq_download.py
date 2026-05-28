"""
NQ Re-download — Extract Document Text for RAG Corpus
======================================================
Problem:  Your current nq_eval.json only has question + gold_answer.
          RAG needs the actual document text to index and retrieve from.

Solution: Re-stream NQ and extract record["document"]["tokens"]
          → reconstruct the Wikipedia page text
          → store it as "context" alongside each question

Output schema (what gets added):
  "context": {
      "title": "Super Bowl XXXIX",
      "text":  "Super Bowl XXXIX was an American football game ..."
  }

Reference:
  Han et al. (2026) §3.1 — "given a corpus, we segment documents
  into textual chunks and build an index"
  record["document"]["tokens"] confirmed present in your terminal output
"""

import json
import os
from datasets import load_dataset

os.makedirs("data", exist_ok=True)

TARGET = 500
SHUFFLE_BUFFER = 2000


# ─────────────────────────────────────────────────────────────
# 1) Extract short answers
# ─────────────────────────────────────────────────────────────
def extract_short_answers(record):
    answers = []

    for ann_dict in record["annotations"]["short_answers"]:
        for text in ann_dict["text"]:
            text = text.strip()
            if text and text not in answers:
                answers.append(text)

    return answers


def has_short_answer(record):
    return len(extract_short_answers(record)) > 0


# ─────────────────────────────────────────────────────────────
# 2) 🔥 FIX: reconstruct real document text from tokens
# ─────────────────────────────────────────────────────────────
def reconstruct_document_text(record):
    tokens = record["document"]["tokens"]["token"]
    is_html = record["document"]["tokens"]["is_html"]

    words = []

    for t, html in zip(tokens, is_html):
        if not html:   # skip HTML
            words.append(t)

    text = " ".join(words)

    # optional cleaning
    text = " ".join(text.split())

    return text


# ─────────────────────────────────────────────────────────────
# 3) Process record
# ─────────────────────────────────────────────────────────────
def process_nq(record, idx):
    answers = extract_short_answers(record)

    title = record["document"]["title"]

    # 🔥 IMPORTANT: use reconstructed text
    context_text = reconstruct_document_text(record)

    # optional truncate (avoid huge docs)
    context_text = context_text[:5000]

    return {
        "id": f"NQ-{str(idx).zfill(4)}",
        "question": record["question"]["text"],
        "gold_answers": answers,
        "gold_answer": answers[0] if answers else "",
        "gold_chunks": [title],
        "question_type": "single-hop",
        "hop_count": 1,
        "answerable": True,
        "dataset": "NQ",

        # ✅ context ready for RAG
        "context": {
            "title": title,
            "text": context_text
        }
    }


# ─────────────────────────────────────────────────────────────
# 4) Load dataset (streaming)
# ─────────────────────────────────────────────────────────────
print("=" * 60)
print("Loading NQ with context reconstruction...")
print("=" * 60)

nq_stream = load_dataset(
    "natural_questions",
    "default",
    split="validation",
    streaming=True
)

nq_stream = nq_stream.shuffle(seed=42, buffer_size=SHUFFLE_BUFFER)


# ─────────────────────────────────────────────────────────────
# 5) Collect data
# ─────────────────────────────────────────────────────────────
collected = []
seen = 0

for record in nq_stream:
    seen += 1

    if not has_short_answer(record):
        continue

    processed = process_nq(record, len(collected))
    collected.append(processed)

    if len(collected) % 100 == 0:
        print(f"Collected {len(collected)}/{TARGET} (scanned {seen})")

    if len(collected) >= TARGET:
        break


print(f"\nDone. Scanned {seen} → collected {len(collected)}")


# ─────────────────────────────────────────────────────────────
# 6) Save
# ─────────────────────────────────────────────────────────────
output_path = "data/nq_eval.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(collected, f, indent=2, ensure_ascii=False)

print(f"\n✅ Saved → {output_path}")


# ─────────────────────────────────────────────────────────────
# 7) Debug sample
# ─────────────────────────────────────────────────────────────
sample = collected[0]

print("\n===== SAMPLE =====")
print("Question:", sample["question"])
print("Answer:", sample["gold_answer"])
print("Title:", sample["context"]["title"])
print("Context preview:", sample["context"]["text"][:300])
print("==================")