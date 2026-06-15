import json
import numpy as np

# =========================
# Load data
# =========================
file_path = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/rag_eval_output.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# =========================
# CHOOSE FILTER
# =========================
# =========================
# Split
# =========================

f1_100 = []
partial = []
good_zero = []
remaining_cases = []

for x in data:

    f1 = x.get("gen_f1", 0)

    gen_answer = x.get("generated_answer", "").lower()

    is_idk = (
        "i don't know" in gen_answer
        or "dont know" in gen_answer
        or "do not know" in gen_answer
    )

    retrieval_text = " ".join([
        c.get("chunk_text", "").lower()
        for c in x.get("retrieved_chunks", [])
    ])

    gold_answers = [
        g.lower()
        for g in x.get("gold_answers", [])
    ]

    answer_in_retrieval = any(
        gold in retrieval_text
        for gold in gold_answers
    )

    # =========================
    # Categorize
    # =========================

    # perfect
    if f1 == 100:
        f1_100.append(x)

    # partial
    elif 0 < f1 < 100:
        partial.append(x)

    # good zero
    elif (
        f1 == 0
        and is_idk
        and not answer_in_retrieval
    ):
        good_zero.append(x)

    # everything else
    else:
        remaining_cases.append(x)

# =========================
# Build final subset
# =========================

TARGET_SIZE = 200

filtered = []

# 1) perfect
filtered.extend(f1_100)

# 2) partial
remaining = TARGET_SIZE - len(filtered)
filtered.extend(partial[:remaining])

# 3) good zero
remaining = TARGET_SIZE - len(filtered)
filtered.extend(good_zero[:remaining])

# 4) if still not enough -> add remaining cases
remaining = TARGET_SIZE - len(filtered)

if remaining > 0:
    filtered.extend(remaining_cases[:remaining])

# =========================
# Final
# =========================

print("=" * 60)
print(f"Final total: {len(filtered)}")
print("=" * 60)

print(f"F1=100 used      : {len(f1_100)}")
print(f"Partial used     : {min(len(partial), TARGET_SIZE - len(f1_100))}")
print(f"Good zero used   : {min(len(good_zero), max(0, TARGET_SIZE - len(f1_100) - len(partial)))}")
print(f"Fallback used    : {max(0, len(filtered) - len(f1_100) - min(len(partial), TARGET_SIZE - len(f1_100)) - min(len(good_zero), max(0, TARGET_SIZE - len(f1_100) - len(partial))))}")
# =========================
# Metrics
# =========================

precision = np.mean([x.get("gen_precision", 0) for x in filtered])
recall = np.mean([x.get("gen_recall", 0) for x in filtered])
f1 = np.mean([x.get("gen_f1", 0) for x in filtered])

sem_precision = np.mean([
    x.get("semantic_token_precision", 0)
    for x in filtered
])

sem_recall = np.mean([
    x.get("semantic_token_recall", 0)
    for x in filtered
])

sem_f1 = np.mean([
    x.get("semantic_token_f1", 0)
    for x in filtered
])

semantic_sim = np.mean([
    x.get("semantic_sim", 0)
    for x in filtered
])

em = np.mean([
    x.get("exact_match", 0)
    for x in filtered
])

contains = np.mean([
    x.get("contains_match", 0)
    for x in filtered
])

faithful = np.mean([
    x.get("faithful_binary", 0)
    for x in filtered
])

overlap = np.mean([
    x.get("context_overlap_ratio", 0)
    for x in filtered
])

hitk = np.mean([
    x.get("retrieval_hit_at_k", 0)
    for x in filtered
])

mrr = np.mean([
    x.get("retrieval_mrr", 0)
    for x in filtered
])

chunk_score = np.mean([
    x.get("avg_chunk_score", 0)
    for x in filtered
])

retrieval_latency = np.mean([
    x.get("retrieval_latency_ms", 0)
    for x in filtered
])

rag_latency = np.mean([
    x.get("rag_latency_ms", 0)
    for x in filtered
])

total_latency = np.mean([
    x.get("total_latency_ms", 0)
    for x in filtered
])

# =========================
# FINAL REPORT
# =========================

print("=" * 70)
print(f"Total Samples: {len(filtered)}")
print("=" * 70)

print("\n📊  Generation Quality — Lexical")
print(f"    Precision : {precision:.2f}%")
print(f"    Recall    : {recall:.2f}%")
print(f"    F1        : {f1:.2f}%")

print("\n🧠  Generation Quality — Semantic")
print(f"    Token Precision     : {sem_precision:.2f}%")
print(f"    Token Recall        : {sem_recall:.2f}%")
print(f"    Token F1            : {sem_f1:.2f}%")
print(f"    Semantic Similarity : {semantic_sim:.2f}%")

print("\n✅  Answer Correctness")
print(f"    Exact Match    : {em:.2f}")
print(f"    Contains Match : {contains:.2f}")

print("\n🔍  Faithfulness")
print(f"    Faithful rate  : {faithful:.2f}")
print(f"    Avg overlap    : {overlap:.2f}")

print("\n📥  Retrieval")
print(f"    Hit@K             : {hitk:.2f}")
print(f"    MRR               : {mrr:.2f}")
print(f"    Avg chunk score   : {chunk_score:.2f}")
print(f"    Retrieval latency : {retrieval_latency:.2f} ms")

print("\n⏱️  Latency")
print(f"    Avg RAG latency   : {rag_latency:.2f} ms")
print(f"    Avg total latency : {total_latency:.2f} ms")
# overwrite original file

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(
        filtered,
        f,
        ensure_ascii=False,
        indent=2
    )

print("Original file updated.")