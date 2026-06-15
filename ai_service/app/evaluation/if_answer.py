import json
import os

CORPUS_DIR = "data/wiki_txt"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def normalize(text):
    return " ".join(text.lower().split())


def contains_answer(text, answers):
    text = normalize(text)
    return any(normalize(ans) in text for ans in answers)


def title_to_filename(title):
    return title.replace(" ", "_") + ".txt"


def load_corpus_by_title(titles):
    for title in titles:
        filename = title_to_filename(title)
        path = os.path.join(CORPUS_DIR, filename)

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

    return ""


# ─────────────────────────────────────────────
# LOAD RESULTS
# ─────────────────────────────────────────────

with open("data/nq_retrieval_results.json") as f:
    results = json.load(f)


# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────

stats = {
    "total": 0,
    "success": 0,
    "retrieval_failure": 0,
    "corpus_missing": 0
}

examples = {
    "retrieval_failure": [],
    "corpus_missing": []
}


for r in results:
    answers = r["gold_answers"]
    retrieved = r["retrieved_texts"]
    titles = r["gold_chunks"]   # 👈 هنا الفرق

    stats["total"] += 1

    # ── retrieval check ───────────────
    in_retrieval = any(
        contains_answer(t, answers) for t in retrieved
    )

    # ── corpus check ──────────────────
    corpus_text = load_corpus_by_title(titles)
    in_corpus = contains_answer(corpus_text, answers)

    # ── classify ──────────────────────
    if in_retrieval:
        stats["success"] += 1

    elif in_corpus:
        stats["retrieval_failure"] += 1

        if len(examples["retrieval_failure"]) < 5:
            examples["retrieval_failure"].append(r["question"])

    else:
        stats["corpus_missing"] += 1

        if len(examples["corpus_missing"]) < 5:
            examples["corpus_missing"].append(r["question"])


# ─────────────────────────────────────────────
# PRINT
# ─────────────────────────────────────────────

print("\n📊 COVERAGE ANALYSIS")
print("="*40)

total = stats["total"]

for k in stats:
    if k != "total":
        print(f"{k}: {stats[k]} ({stats[k]/total*100:.2f}%)")

print("\n🔍 Examples:")

print("\nRetrieval Failures:")
for q in examples["retrieval_failure"]:
    print("-", q)

print("\nCorpus Missing:")
for q in examples["corpus_missing"]:
    print("-", q)