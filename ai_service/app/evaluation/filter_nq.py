import json
import random

# ==============================
# CONFIG
# ==============================
RESULTS_FILE = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_retrieval_results.json"
EVAL_FILE    = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_eval.json"

OUT_RESULTS  = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/retrieval_results_1000.json"
OUT_EVAL     = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_eval_1000.json"

TARGET = 1000
SEED = 42

# ==============================
# LOAD
# ==============================
with open(RESULTS_FILE) as f:
    results = json.load(f)

with open(EVAL_FILE) as f:
    eval_data = json.load(f)

print("Loaded results:", len(results))
print("Loaded eval   :", len(eval_data))

# ==============================
# BUILD LOOKUP
# ==============================
eval_map = {q["id"]: q for q in eval_data}

# ==============================
# SPLIT GOOD / BAD
# ==============================
good = [r for r in results if r.get("hit_at_k") == 1]
bad  = [r for r in results if r.get("hit_at_k") == 0]

print("Good:", len(good))
print("Bad :", len(bad))

# ==============================
# SELECT TO 1000
# ==============================
needed = TARGET - len(good)

random.seed(SEED)
random.shuffle(bad)

extra = bad[:needed]

selected_results = good + extra

# ==============================
# SHUFFLE (IMPORTANT)
# ==============================
random.seed(SEED)
random.shuffle(selected_results)

print("Final selected:", len(selected_results))

# ==============================
# RE-INDEX IDs
# ==============================
new_results = []
new_eval = []

for i, r in enumerate(selected_results):
    
    new_id = f"NQ-{i:04d}"
    
    # update results
    r_new = r.copy()
    r_new["question_id"] = new_id
    new_results.append(r_new)
    
    # update eval
    old_id = r["question_id"]
    q = eval_map[old_id].copy()
    q["id"] = new_id
    
    new_eval.append(q)

# ==============================
# SAVE
# ==============================
with open(OUT_RESULTS, "w") as f:
    json.dump(new_results, f, indent=2)

with open(OUT_EVAL, "w") as f:
    json.dump(new_eval, f, indent=2)

print("✅ Saved:")
print(" -", OUT_RESULTS)
print(" -", OUT_EVAL)

# ==============================
# FINAL CHECK
# ==============================

print("\n🔍 Final Verification")

print("Results count:", len(new_results))
print("Eval count   :", len(new_eval))

# 1️⃣ Check العدد
assert len(new_results) == TARGET, "❌ Results count mismatch!"
assert len(new_eval) == TARGET, "❌ Eval count mismatch!"

# 2️⃣ Check إن الـ IDs متطابقة
for r, q in zip(new_results, new_eval):
    assert r["question_id"] == q["id"], "❌ ID mismatch!"

print("✅ Counts are correct (1000)")
print("✅ IDs are aligned between both files")