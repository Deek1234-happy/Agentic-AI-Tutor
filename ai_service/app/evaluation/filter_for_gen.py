import json
import random

input_path = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_retrieval_results.json"

output_path = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_filtered_results.json"

# Load data
with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# =========================
# Keep ALL MRR = 1
# =========================
mrr_1 = [item for item in data if item.get("mrr") == 1]

# Take from 0 and 0.5 to complete 800
others = [
    item for item in data
    if item.get("mrr") in [0, 0.5]
]

needed = max(0, 800 - len(mrr_1))

sampled_others = random.sample(
    others,
    min(needed, len(others))
)

# Final filtered dataset
filtered = mrr_1 + sampled_others

# Shuffle final data
random.shuffle(filtered)

# Save file
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

# =========================
# Statistics
# =========================
total = len(filtered)

hit10 = sum(item["hit_at_k"] for item in filtered) / total
hit1 = sum(item["hit_at_1"] for item in filtered) / total
mrr_avg = sum(item["mrr"] for item in filtered) / total

count_1 = sum(1 for x in filtered if x["mrr"] == 1)
count_05 = sum(1 for x in filtered if x["mrr"] == 0.5)
count_0 = sum(1 for x in filtered if x["mrr"] == 0)

print("==================================================")
print(f"Questions After Filter : {total}")
print()

print(f"MRR = 1     : {count_1}")
print(f"MRR = 0.5   : {count_05}")
print(f"MRR = 0     : {count_0}")
print()

print(f"Hit@10 : {hit10 * 100:.1f}%")
print(f"Hit@1  : {hit1 * 100:.1f}%")
print(f"MRR    : {mrr_avg * 100:.2f}%")
print("==================================================")

print(f"\nFiltered file saved to:\n{output_path}")