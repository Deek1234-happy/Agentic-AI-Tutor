# # kg_retrieval_eval.py
# """
# KG Retrieval Evaluation (Natural Questions)
# ===========================================

# Evaluates ONLY the Knowledge Graph retrieval pipeline.

# Pipeline:
# ---------
# Question
#    ↓
# POST /kg/query/subject
#    ↓
# Retrieve entities + relationships
#    ↓
# Check if gold answer exists in retrieved graph
#    ↓
# Compute:
#     - Hit@1
#     - Hit@K
#     - MRR
#     - Avg latency

# Input:
# ------
# /home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_questions_final_500.json

# Example question format:
# [
#   {
#     "id": 401,
#     "question": "what year did seven nation army come out",
#     "answers": ["march 2003", "2003"],
#     "context_file": "doc_401.txt"
#   }
# ]

# Output:
# -------
# data/kg_retrieval_results.json
# data/kg_retrieval_metrics.json
# """

# import json
# import re
# import time
# import os
# import requests

# # ============================================================
# # CONFIG
# # ============================================================

# BASE_URL = "http://localhost:8000"

# KG_QUERY_URL = f"{BASE_URL}/kg/query/subject"

# QUESTIONS_FILE = "data/nq_questions_final_500.json"

# RESULTS_FILE = "data/kg_retrieval_results.json"
# METRICS_FILE = "data/kg_retrieval_metrics.json"

# # IMPORTANT:
# # use real IDs from your DB
# USER_ID = "0a222ef4-81ab-4d90-81c1-4a6eaf4d8330"
# SUBJECT_ID = "082a9538-9f2d-4d97-b53c-14e6d1ba05b2"

# K = 10
# HOPS = 1

# CHECKPOINT_EVERY = 10

# READY_DOC_IDS = [
#     "21e91467-3573-421d-b303-57188bb24d5a",
#     "fbe4a468-d6d4-4ec5-bd51-ea46357fb85b",
#     "1a6330df-8d45-4937-9211-7ab4cdc8ba16",
#     "bb66a655-6ad3-41f2-9d82-4219182cc1de",
#     "7c35f3fa-f9e7-4ac1-b852-0d2496ca3ed4",
#     "c8fcc2ff-535f-4fbc-9379-e5bda4718bd7",
#     "2de76ff0-865d-42b9-83f1-1e1929e37ab7",
#     "455baf44-8d1c-49c6-acc3-069a862c6f8e",
#     "1ac8ece3-e86c-40bf-aa55-beb287e91efa",
#     "c1a732e2-c0a7-4fae-a3c9-d9b1e65748f6",
#     "8c007153-3339-44ca-b65c-4f08002c9fc7",
#     "13b4a9ef-2cd5-484b-ad65-9bcce48f18ae",
#     "2b63dbda-bf12-48ed-ab81-d1866d764f0f",
#     "93fd752d-429d-4ebd-ace1-8b91f7d699b8",
#     "eb439fb1-ca17-46df-b979-073a717f7134",
#     "fb643a2f-e677-40a5-a147-c0c043499f7b",
#     "71d4e631-d3a0-458a-8134-aeaf0430a213",
# ]
# READY_CONTEXT_FILES = {
#     "doc_0.txt",
#     "doc_1.txt",
#     "doc_10.txt",
#     "doc_100.txt",
#     "doc_101.txt",
#     "doc_102.txt",
#     "doc_103.txt",
#     "doc_104.txt",
#     "doc_105.txt",
#     "doc_109.txt",
#     "doc_112.txt",
#     "doc_113.txt",
#     "doc_114.txt",
#     "doc_115.txt",
#     "doc_116.txt",
#     "doc_119.txt",
#     "doc_122.txt",
# }
# CONTEXT_TO_DOC_ID = {
#     "doc_0.txt": "71d4e631-d3a0-458a-8134-aeaf0430a213",
#     "doc_1.txt": "fb643a2f-e677-40a5-a147-c0c043499f7b",
#     "doc_10.txt": "eb439fb1-ca17-46df-b979-073a717f7134",
#     "doc_100.txt": "93fd752d-429d-4ebd-ace1-8b91f7d699b8",
#     "doc_101.txt": "2b63dbda-bf12-48ed-ab81-d1866d764f0f",
#     "doc_102.txt": "13b4a9ef-2cd5-484b-ad65-9bcce48f18ae",
#     "doc_103.txt": "8c007153-3339-44ca-b65c-4f08002c9fc7",
#     "doc_104.txt": "c1a732e2-c0a7-4fae-a3c9-d9b1e65748f6",
#     "doc_105.txt": "1ac8ece3-e86c-40bf-aa55-beb287e91efa",
#     "doc_109.txt": "455baf44-8d1c-49c6-acc3-069a862c6f8e",
#     "doc_112.txt": "2de76ff0-865d-42b9-83f1-1e1929e37ab7",
#     "doc_113.txt": "c8fcc2ff-535f-4fbc-9379-e5bda4718bd7",
#     "doc_114.txt": "7c35f3fa-f9e7-4ac1-b852-0d2496ca3ed4",
#     "doc_115.txt": "bb66a655-6ad3-41f2-9d82-4219182cc1de",
#     "doc_116.txt": "1a6330df-8d45-4937-9211-7ab4cdc8ba16",
#     "doc_119.txt": "fbe4a468-d6d4-4ec5-bd51-ea46357fb85b",
#     "doc_122.txt": "21e91467-3573-421d-b303-57188bb24d5a",
# }

# os.makedirs("data", exist_ok=True)

# # ============================================================
# # NORMALIZATION
# # ============================================================

# def normalize_text(text: str) -> str:

#     text = text.lower()

#     text = re.sub(r"[^a-z0-9 ]", " ", text)

#     text = re.sub(r"\s+", " ", text)

#     return text.strip()


# # ============================================================
# # ANSWER MATCHING
# # ============================================================

# def kg_contains_answer(subgraph: dict, gold_answers: list):

#     entities = subgraph.get("entities", [])
#     relationships = subgraph.get("relationships", [])

#     collected = []

#     # entities
#     for e in entities:

#         name = e.get("name", "")

#         if name:
#             collected.append(name)

#     # relationships
#     for r in relationships:

#         text = (
#             f"{r.get('source', '')} "
#             f"{r.get('relation', '')} "
#             f"{r.get('target', '')}"
#         )

#         collected.append(text)

#     combined = normalize_text(" ".join(collected))

#     for ans in gold_answers:

#         norm_ans = normalize_text(ans)

#         if norm_ans in combined:
#             return True

#     return False


# # ============================================================
# # ENTITY RANKING
# # ============================================================

# def rank_entities(subgraph: dict, gold_answers: list):

#     ranked = []

#     entities = subgraph.get("entities", [])

#     for ent in entities:

#         name = ent.get("name", "")

#         relevant = False

#         for ans in gold_answers:

#             if normalize_text(ans) in normalize_text(name):
#                 relevant = True
#                 break

#         ranked.append({
#             "entity": name,
#             "relevant": relevant
#         })

#     # relevant first
#     ranked.sort(key=lambda x: x["relevant"], reverse=True)

#     return ranked


# # ============================================================
# # METRICS
# # ============================================================

# def compute_metrics(ranked_entities, k=K):

#     top_k = ranked_entities[:k]

#     hit_at_k = int(any(e["relevant"] for e in top_k))

#     hit_at_1 = 0

#     if top_k:
#         hit_at_1 = int(top_k[0]["relevant"])

#     mrr = 0.0

#     for idx, e in enumerate(top_k, start=1):

#         if e["relevant"]:

#             mrr = 1.0 / idx
#             break

#     return {
#         "hit_at_k": hit_at_k,
#         "hit_at_1": hit_at_1,
#         "mrr": round(mrr, 4),
#     }


# # ============================================================
# # KG RETRIEVAL CALL
# # ============================================================

# def call_kg_retrieval(question: str, document_id: str):

#     response = requests.post(
#         KG_QUERY_URL,
#         json={
#             "question": question,
#             "subject_id": SUBJECT_ID,
#             "user_id": USER_ID,
#             "document_ids": [document_id],
#             "hops": 1,
#             "flexible_seed_match": True
#         },
#         timeout=300,
#     )

#     response.raise_for_status()

#     return response.json()


# # ============================================================
# # SAVE HELPERS
# # ============================================================

# def save_json_atomic(path: str, payload):

#     tmp_path = f"{path}.tmp"

#     with open(tmp_path, "w", encoding="utf-8") as f:
#         json.dump(payload, f, indent=2, ensure_ascii=False)

#     os.replace(tmp_path, path)


# # ============================================================
# # MAIN EVALUATION
# # ============================================================

# def run_kg_retrieval_evaluation():

#     print("=" * 70)
#     print("KG RETRIEVAL EVALUATION")
#     print("=" * 70)

#     print(f"Endpoint : {KG_QUERY_URL}")
#     print(f"K        : {K}")
#     print(f"Hops     : {HOPS}")

#     print("=" * 70)

#     with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
#         questions = json.load(f)
#         questions = [
#                     q for q in questions
#                     if q["context_file"] in READY_CONTEXT_FILES
#                 ]

#     print(f"\nLoaded {len(questions)} questions\n")

#     results = []

#     total_latency = 0

#     failed = []

#     # ========================================================
#     # RESUME SUPPORT
#     # ========================================================

#     if os.path.exists(RESULTS_FILE):

#         with open(RESULTS_FILE, "r", encoding="utf-8") as f:
#             results = json.load(f)

#         print(f"Loaded checkpoint: {len(results)} results")

#     processed_ids = {
#         r["question_id"]
#         for r in results
#     }

#     # ========================================================
#     # LOOP
#     # ========================================================

#     for idx, q in enumerate(questions):

#         if q["id"] in processed_ids:
#             continue

#         question = q["question"]

#         answers = q["answers"]

#         print(f"\n[{idx+1}/{len(questions)}]")
#         print(f"Q: {question}")

#         start = time.time()

#         try:

#             document_id = CONTEXT_TO_DOC_ID[q["context_file"]]

#             subgraph = call_kg_retrieval(
#                 question,
#                 document_id
# )

#             latency_ms = int((time.time() - start) * 1000)

#             total_latency += latency_ms

#             entities = subgraph.get("entities", [])

#             relationships = subgraph.get("relationships", [])

#             ranked = rank_entities(subgraph, answers)

#             metrics = compute_metrics(ranked)

#             answer_found = kg_contains_answer(
#                 subgraph,
#                 answers
#             )

#             result = {

#                 # gold
#                 "question_id": q["id"],
#                 "question": question,
#                 "answers": answers,

#                 # retrieved graph
#                 "entities_retrieved": len(entities),
#                 "relationships_retrieved": len(relationships),

#                 "entities": entities,
#                 "relationships": relationships,

#                 # metrics
#                 "answer_found": answer_found,

#                 "hit_at_k": metrics["hit_at_k"],
#                 "hit_at_1": metrics["hit_at_1"],
#                 "mrr": metrics["mrr"],

#                 "latency_ms": latency_ms,
#             }

#             results.append(result)

#             print(
#                 f"Entities={len(entities)} | "
#                 f"Relationships={len(relationships)} | "
#                 f"Hit@K={metrics['hit_at_k']} | "
#                 f"MRR={metrics['mrr']}"
#             )

#         except Exception as e:

#             print(f"FAILED: {e}")

#             failed.append(q["id"])

#             results.append({

#                 "question_id": q["id"],
#                 "question": question,
#                 "answers": answers,

#                 "entities_retrieved": 0,
#                 "relationships_retrieved": 0,

#                 "entities": [],
#                 "relationships": [],

#                 "answer_found": False,

#                 "hit_at_k": 0,
#                 "hit_at_1": 0,
#                 "mrr": 0.0,

#                 "latency_ms": 0,

#                 "error": str(e),
#             })

#         # ====================================================
#         # CHECKPOINT
#         # ====================================================

#         if len(results) % CHECKPOINT_EVERY == 0:

#             save_json_atomic(RESULTS_FILE, results)

#             print(f"\nCheckpoint saved ({len(results)} results)")

#         # ====================================================
#         # PROGRESS
#         # ====================================================

#         if len(results) % 100 == 0:

#             valid = [
#                 r for r in results
#                 if "error" not in r
#             ]

#             avg_hitk = (
#                 sum(r["hit_at_k"] for r in valid) / len(valid)
#                 if valid else 0
#             )

#             avg_hit1 = (
#                 sum(r["hit_at_1"] for r in valid) / len(valid)
#                 if valid else 0
#             )

#             avg_mrr = (
#                 sum(r["mrr"] for r in valid) / len(valid)
#                 if valid else 0
#             )

#             print("\n" + "-" * 50)

#             print(
#                 f"Progress: {len(results)}/{len(questions)}"
#             )

#             print(
#                 f"Hit@{K}: {avg_hitk*100:.2f}%"
#             )

#             print(
#                 f"Hit@1: {avg_hit1*100:.2f}%"
#             )

#             print(
#                 f"MRR: {avg_mrr*100:.2f}%"
#             )

#             print("-" * 50)

#     # ========================================================
#     # FINAL SAVE
#     # ========================================================

#     save_json_atomic(RESULTS_FILE, results)

#     valid = [
#         r for r in results
#         if "error" not in r
#     ]

#     def avg(field):

#         if not valid:
#             return 0.0

#         return round(
#             100 * sum(r[field] for r in valid) / len(valid),
#             2
#         )

#     metrics_summary = {

#         "Hit@K": avg("hit_at_k"),
#         "Hit@1": avg("hit_at_1"),
#         "MRR": avg("mrr"),

#         "K": K,
#         "Hops": HOPS,

#         "n_questions": len(questions),
#         "n_valid": len(valid),
#         "n_failed": len(failed),

#         "avg_latency_ms": round(
#             total_latency / len(questions),
#             2
#         ) if questions else 0,
#     }

#     save_json_atomic(METRICS_FILE, metrics_summary)

#     # ========================================================
#     # FINAL PRINT
#     # ========================================================

#     print("\n" + "=" * 70)
#     print("FINAL RESULTS")
#     print("=" * 70)

#     print(f"Hit@{K} : {metrics_summary['Hit@K']}%")
#     print(f"Hit@1   : {metrics_summary['Hit@1']}%")
#     print(f"MRR     : {metrics_summary['MRR']}%")

#     print(f"Latency : {metrics_summary['avg_latency_ms']} ms")

#     print("=" * 70)

#     return metrics_summary


# # ============================================================
# # ENTRY
# # ============================================================

# if __name__ == "__main__":

#     run_kg_retrieval_evaluation()

# kg_retrieval_eval.py
"""
KG Retrieval Evaluation — Paper-Aligned (Table 16 methodology)
===============================================================

PRIMARY METRIC (matches the paper's KG-GraphRAG Triplets-only retrieval mode):
    retrieval_accuracy = proportion of questions where the gold
    answer string appears anywhere in the retrieved relationship
    triples: (source relation target).

SECONDARY METRICS (standard IR, not in paper):
    Hit@K  = answer entity in top-K entity names
    Hit@1  = answer entity is first returned entity
    MRR    = 1/rank of first relevant entity

FIXES vs original script:
    1. normalize_text   : unicode-aware (fixes Röntgen, etc.)
    2. retrieval_accuracy: flat string search over full context blob
                          (paper-identical — entities + triple text)
    3. rank_entities    : bidirectional overlap, TRUE retrieval order
    4. hit_at_1         : honest positional metric (no pre-sort)
    5. latency          : tracked per-run only (correct on resume)
    6. question_type    : entity vs descriptive split in summary
    7. seed_miss        : flagged separately (0-entity responses)
"""

import json
import re
import time
import os
import unicodedata
import requests

# ============================================================
# CONFIG
# ============================================================

BASE_URL      = "http://localhost:8000"
KG_QUERY_URL  = f"{BASE_URL}/kg/query/subject"
QUESTIONS_FILE = "data/nq_questions_final_500.json"
RESULTS_FILE   = "data/kg_retrieval_results.json"
METRICS_FILE   = "data/kg_retrieval_metrics.json"

USER_ID    = "0a222ef4-81ab-4d90-81c1-4a6eaf4d8330"
SUBJECT_ID = "082a9538-9f2d-4d97-b53c-14e6d1ba05b2"

K                = 10
HOPS             = 2 # 1 
CHECKPOINT_EVERY = 10
CONTEXT_MODE     = "triples_only"



CONTEXT_TO_DOC_ID = {
    "doc_100.txt": "8faded88-1fdc-4215-b0f1-9d068c8ca43e",
    "doc_101.txt": "26b1ba5e-cb3c-486d-bd7a-429031c3bfed",
    "doc_102.txt": "b605f094-eb8b-462b-b7f3-401348b20a01",
    "doc_103.txt": "d9395d2c-62ee-437a-9ee1-fd5031f4f6a4",
    "doc_104.txt": "4764b1eb-9119-4e28-919b-aa6d8e947b40",
    "doc_105.txt": "e66131d3-fe10-4529-9382-39b619de73cc",
    "doc_108.txt": "ab4c0eeb-3eba-4f40-9cf8-9de9e9ea7f5a",
    "doc_109.txt": "f4818875-e0bd-4a78-81c2-07a00bdbd061",
    "doc_110.txt": "8416caf7-8899-4086-8ab6-eafc3fb65431",
    "doc_112.txt": "31d4fae1-b203-42d8-8c08-6823cb6f8527",
    "doc_113.txt": "6aab1561-4676-421d-be76-c99ba6cf5267",
    "doc_114.txt": "ad282c28-9c4b-4526-9e25-6b44f9fd5a2c",
    "doc_115.txt": "03d0a833-4fb5-4323-bf71-4bdac2ec0304",
    "doc_116.txt": "9f8c2081-2563-48d0-9576-6fc5f87fafe0",
    "doc_119.txt": "96794ad1-1224-427a-99e9-642947d3b2c8",
    "doc_122.txt": "e227079c-f4ca-4234-b14e-88e806854bc3",
    "doc_125.txt": "942a89fb-1477-4823-8902-c0cc1ee088cb",
    "doc_126.txt": "6d666720-3272-4438-8307-c77fd1cd8428",
    "doc_129.txt": "a387cb67-6a46-4249-9bea-bde65dce6199",
    "doc_131.txt": "c7451bd8-30d0-4f7e-b588-450ddd5fc7f7",
    "doc_140.txt": "e0465acf-54de-4eee-81b7-9da5ba50b1d0",
    "doc_141.txt": "5c046043-0f68-4ef0-9781-f1756a419b5f",
    "doc_148.txt": "242fb4de-6ac4-4ef1-b4bd-7b710d156dc7",
    "doc_149.txt": "e7aaae0a-ae25-44c2-93ba-49b8c1066b27",
    "doc_150.txt": "bf0bdb2f-7078-412e-810c-b79dbfb1d916",
    "doc_151.txt": "ee627c89-b8f4-4cd0-bd05-83281641fd8c",
    "doc_157.txt": "1a6be2f1-284b-4792-bdf9-acb9cd40164f",
    "doc_158.txt": "95887d74-d6aa-456b-b8e8-922caef9759a",
    "doc_159.txt": "07186fc4-8ef1-4087-a774-765df9c2243f",
    "doc_16.txt":  "82eba157-a9ca-41e4-b5ea-645396be5690",
    "doc_161.txt": "7d04476e-cade-4546-bc77-180badee9809",
    "doc_163.txt": "cf8b80d7-ae48-48d9-92d6-faaccb1052d5",
    "doc_167.txt": "16aa057b-4620-4427-b914-bd6cb3da0e97",
    "doc_168.txt": "0d909c22-8e45-4b22-818b-97dec24c3c75",
    "doc_171.txt": "b9c0afde-5768-4dc5-a11c-0726172845db",
    "doc_173.txt": "69f042b1-9095-47d8-b407-ec9d890bbce0",
    "doc_175.txt": "af5c52dd-0d8c-43df-93a9-1b8aa21a9f49",
    "doc_177.txt": "c059eb4e-bbe2-4f1b-bfd3-18988346c602",
    "doc_18.txt":  "5e0f3195-2ed9-4f3c-b8cc-eade51921896",
    "doc_180.txt": "0545a392-07cb-477a-9cb5-5825abeb1edf",
    "doc_181.txt": "52312324-9a3d-43fd-b9aa-f0af5ef3dedd",
}



READY_CONTEXT_FILES = set(CONTEXT_TO_DOC_ID.keys())
READY_DOC_IDS = list(CONTEXT_TO_DOC_ID.values())

os.makedirs("data", exist_ok=True)


# ============================================================
# NORMALIZATION — unicode-aware
# ============================================================

def normalize_text(text: str) -> str:
    """
    NFKD decompose → drop accent marks → lowercase → strip
    non-alphanumeric → collapse whitespace.
    Handles: Röntgen→rontgen, Etienne→etienne, etc.
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# QUESTION TYPE — entity vs descriptive
# ============================================================

_DESCRIPTIVE_PREFIXES = (
    "what happens", "what purpose", "what does", "how does",
    "how many",     "why does",     "what are",  "what is the process",
    "what effect",  "what role",    "what type",
)
_ENTITY_PREFIXES = (
    "who", "when", "where", "which", "what year", "what date",
    "what is", "what was", "what were",
)

def classify_question(question: str) -> str:
    q = question.lower().strip()
    for p in _DESCRIPTIVE_PREFIXES:
        if q.startswith(p):
            return "descriptive"
    for p in _ENTITY_PREFIXES:
        if q.startswith(p):
            return "entity"
    return "entity"


# ============================================================
# PRIMARY METRIC — paper Table 16 style
# ============================================================
  
def build_context_blob(subgraph: dict) -> str:
    """
    KG-GraphRAG (Triplets only): concatenate only retrieved triples.
    Standalone entity names are intentionally excluded from the primary
    retrieval_accuracy metric.
    """
    parts = []
    # include entity names (catches cases where answer = entity name)
    for e in subgraph.get("entities", []):
        name = e.get("name", "")
        etype = e.get("type", "")
        if name:
            parts.append(f"{name} {etype}")
    # include relationship triples
    for r in subgraph.get("relationships", []):
        triple = (
            f"{r.get('source', '')} "
            f"{r.get('relation', '')} "
            f"{r.get('target', '')}"
        )
        parts.append(triple)
    return normalize_text(" ".join(parts))

# def retrieval_accuracy_hit(subgraph: dict, gold_answers: list) -> bool:
#     """
#     TABLE 16 METRIC: returns True if any gold answer string appears
#     anywhere in the full retrieved context blob.
#     Comparable directly to the paper's reported retrieval accuracy %.
#     """
#     blob = build_context_blob(subgraph)
#     for ans in gold_answers:
#         norm_ans = normalize_text(ans)
#         if norm_ans and norm_ans in blob:
#             return True
#     return False
_STOPWORDS = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or"}

def _remove_stopwords(text: str) -> str:
    return " ".join(w for w in text.split() if w not in _STOPWORDS)

def retrieval_accuracy_hit(subgraph: dict, gold_answers: list) -> bool:
    blob = build_context_blob(subgraph)
    blob_no_stop = _remove_stopwords(blob)
    for ans in gold_answers:
        norm_ans = normalize_text(ans)
        if norm_ans and norm_ans in blob:
            return True
        # stopword-tolerant fallback
        norm_ans_no_stop = _remove_stopwords(norm_ans)
        if norm_ans_no_stop and norm_ans_no_stop in blob_no_stop:
            return True
    return False


# ============================================================
# SECONDARY METRICS — entity-name ranking (IR style)
# ============================================================

def entity_matches_answer(entity_name: str, gold_answers: list) -> bool:
    """
    Bidirectional substring overlap between entity name and any gold answer.
    - "Nepal" matches answer "nepal"  (answer in name)
    - "Dollree Mapp" matches answer "dollree mapp"  (name in answer)
    """
    norm_name = normalize_text(entity_name)
    if not norm_name:
        return False
    for ans in gold_answers:
        norm_ans = normalize_text(ans)
        if not norm_ans:
            continue
        if norm_ans in norm_name or norm_name in norm_ans:
            return True
    return False


def rank_entities(subgraph: dict, gold_answers: list) -> list:
    """
    Preserve TRUE retrieval order — no sorting.
    Sorting would make Hit@1 meaningless.
    """
    return [
        {
            "entity":   e.get("name", ""),
            "relevant": entity_matches_answer(e.get("name", ""), gold_answers),
        }
        for e in subgraph.get("entities", [])
    ]


def compute_ir_metrics(ranked: list, k: int = K) -> dict:
    """
    Hit@1 = first returned entity is relevant
    Hit@K = any of top-K entities is relevant
    MRR   = 1/rank of first relevant entity in top-K
    All computed on TRUE retrieval order.
    """
    top_k = ranked[:k]

    hit_at_1 = int(bool(top_k) and top_k[0]["relevant"])
    hit_at_k = int(any(e["relevant"] for e in top_k))

    mrr = 0.0
    for idx, e in enumerate(top_k, start=1):
        if e["relevant"]:
            mrr = 1.0 / idx
            break

    return {
        "hit_at_k": hit_at_k,
        "hit_at_1": hit_at_1,
        "mrr":      round(mrr, 4),
    }


# ============================================================
# KG RETRIEVAL CALL
# ============================================================

def call_kg_retrieval(question: str, document_id: str) -> dict:
    response = requests.post(
        KG_QUERY_URL,
        json={
            "question":         question,
            "subject_id":       SUBJECT_ID,
            "user_id":          USER_ID,
            "document_ids":     [document_id],
            "hops":             HOPS,
            "flexible_seed_match": True,
            "include_source_text": False,
            "use_llm_query_entities": False,
        },
        timeout=120,   # fail fast — don't hang for 5 min
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# ATOMIC SAVE
# ============================================================

def save_json_atomic(path: str, payload):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ============================================================
# SUMMARY — paper-comparable + IR breakdown
# ============================================================

def compute_summary(results: list, n_total: int, run_latency_ms: int) -> dict:
    valid   = [r for r in results if "error" not in r]
    entity  = [r for r in valid if r.get("question_type") == "entity"]
    desc    = [r for r in valid if r.get("question_type") == "descriptive"]
    seeded  = [r for r in valid if r.get("entities_retrieved", 0) > 0]
    no_seed = [r for r in valid if r.get("entities_retrieved", 0) == 0]

    def pct(items, field):
        if not items:
            return 0.0
        return round(100 * sum(r[field] for r in items) / len(items), 2)

    return {
        # ── PRIMARY: paper Table-16-comparable ─────────────────────────
        # "proportion of examples where gold answer appears in retrieved context"
        "retrieval_accuracy_all":         pct(valid,  "retrieval_accuracy"),
        "retrieval_accuracy_entity_q":    pct(entity, "retrieval_accuracy"),
        "retrieval_accuracy_descriptive_q": pct(desc, "retrieval_accuracy"),
        "retrieval_accuracy_seeded":      pct(seeded, "retrieval_accuracy"),  # excl. seed misses

        # ── SECONDARY: IR ranking metrics ──────────────────────────────
        "Hit_at_K_entity":  pct(entity, "hit_at_k"),
        "Hit_at_1_entity":  pct(entity, "hit_at_1"),
        "MRR_entity":       pct(entity, "mrr"),
        "Hit_at_K_all":     pct(valid,  "hit_at_k"),
        "Hit_at_1_all":     pct(valid,  "hit_at_1"),
        "MRR_all":          pct(valid,  "mrr"),

        # ── DIAGNOSTICS ────────────────────────────────────────────────
        "seed_miss_rate": round(100 * len(no_seed) / len(valid), 2) if valid else 0,

        # ── COUNTS ─────────────────────────────────────────────────────
        "K":    K,
        "Hops": HOPS,
        "n_total":        n_total,
        "n_valid":        len(valid),
        "n_entity_q":     len(entity),
        "n_descriptive_q": len(desc),
        "n_seed_miss":    len(no_seed),
        "n_failed":       len(results) - len(valid),

        "avg_latency_ms_this_run": round(
            run_latency_ms / len(seeded), 2
        ) if seeded else 0,
    }


# ============================================================
# MAIN
# ============================================================

def run_kg_retrieval_evaluation():

    print("=" * 70)
    print("KG RETRIEVAL EVALUATION  (paper-aligned)")
    print("=" * 70)
    print(f"Endpoint : {KG_QUERY_URL}")
    print(f"K        : {K}  |  Hops : {HOPS}")
    print("Primary metric : retrieval_accuracy (Table 16 style)")
    print("=" * 70)

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        all_q = json.load(f)
    questions = [q for q in all_q if q["context_file"] in READY_CONTEXT_FILES]
    print(f"\nLoaded {len(questions)} questions\n")

    # resume
    results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
        original_count = len(results)
        results = [r for r in results if r.get("context_mode") == CONTEXT_MODE]
        print(f"Resumed from checkpoint: {len(results)} results")
        if original_count != len(results):
            print(
                f"Ignored {original_count - len(results)} stale result(s) "
                f"from a different retrieval context mode."
            )

    processed_ids  = {r["question_id"] for r in results}
    run_latency_ms = 0
    run_count      = 0
    failed         = []

    for idx, q in enumerate(questions):

        if q["id"] in processed_ids:
            continue

        question    = q["question"]
        answers     = q["answers"]
        q_type      = classify_question(question)
        document_id = CONTEXT_TO_DOC_ID[q["context_file"]]

        print(f"\n[{idx+1}/{len(questions)}] [{q_type}]")
        print(f"Q  : {question}")
        print(f"Ans: {answers}")

        start = time.time()

        try:
            subgraph   = call_kg_retrieval(question, document_id)
            latency_ms = int((time.time() - start) * 1000)
            run_latency_ms += latency_ms
            run_count      += 1

            entities      = subgraph.get("entities", [])
            relationships = subgraph.get("relationships", [])
            seed_miss     = len(entities) == 0 and len(relationships) == 0

            # ── PRIMARY metric (paper Table 16) ──────────────────────
            ret_acc = retrieval_accuracy_hit(subgraph, answers)

            # ── SECONDARY metrics (IR ranking) ───────────────────────
            ranked  = rank_entities(subgraph, answers)
            ir      = compute_ir_metrics(ranked)

            result = {
                # identifiers
                "question_id":   q["id"],
                "question":      question,
                "question_type": q_type,
                "context_mode":  CONTEXT_MODE,
                "answers":       answers,

                # retrieval stats
                "entities_retrieved":      len(entities),
                "relationships_retrieved": len(relationships),
                "seed_miss":               seed_miss,

                # PRIMARY — paper-comparable
                "retrieval_accuracy": ret_acc,

                # SECONDARY — IR ranking
                "hit_at_k": ir["hit_at_k"],
                "hit_at_1": ir["hit_at_1"],
                "mrr":      ir["mrr"],

                # raw data (keep for debugging)
                "entities":      entities,
                "relationships": relationships,

                "latency_ms": latency_ms,
            }

            results.append(result)

            print(
                f"Ents={len(entities):3d} | Rels={len(relationships):3d} | "
                f"ret_acc={int(ret_acc)} | "
                f"Hit@K={ir['hit_at_k']} | Hit@1={ir['hit_at_1']} | "
                f"MRR={ir['mrr']:.2f} | "
                f"seed_miss={seed_miss} | {latency_ms}ms"
            )

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            print(f"  FAILED ({latency_ms}ms): {e}")
            failed.append(q["id"])

            results.append({
                "question_id":   q["id"],
                "question":      question,
                "question_type": q_type,
                "context_mode":  CONTEXT_MODE,
                "answers":       answers,

                "entities_retrieved":      0,
                "relationships_retrieved": 0,
                "seed_miss":               True,

                "retrieval_accuracy": False,
                "hit_at_k": 0,
                "hit_at_1": 0,
                "mrr":      0.0,

                "entities":      [],
                "relationships": [],

                "latency_ms": latency_ms,
                "error":      str(e),
            })

        # checkpoint
        if len(results) % CHECKPOINT_EVERY == 0:
            save_json_atomic(RESULTS_FILE, results)
            print(f"  [checkpoint — {len(results)} results saved]")

        # mid-run progress
        if run_count > 0 and run_count % 50 == 0:
            s = compute_summary(results, len(questions), run_latency_ms)
            print(f"\n{'─'*60}")
            print(f"  Progress : {len(results)}/{len(questions)}")
            print(f"  retrieval_accuracy (all)    : {s['retrieval_accuracy_all']}%")
            print(f"  retrieval_accuracy (entity) : {s['retrieval_accuracy_entity_q']}%")
            print(f"  seed_miss_rate              : {s['seed_miss_rate']}%")
            print(f"  Hit@K / Hit@1 / MRR (entity): "
                  f"{s['Hit_at_K_entity']}% / {s['Hit_at_1_entity']}% / {s['MRR_entity']}%")
            print(f"{'─'*60}\n")

    # final save
    save_json_atomic(RESULTS_FILE, results)
    summary = compute_summary(results, len(questions), run_latency_ms)
    save_json_atomic(METRICS_FILE, summary)

    # ── FINAL PRINT ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"  Questions : {summary['n_total']}  "
          f"(entity={summary['n_entity_q']}, "
          f"descriptive={summary['n_descriptive_q']})")
    print(f"  Failed    : {summary['n_failed']}")
    print(f"  Seed miss : {summary['n_seed_miss']}  "
          f"({summary['seed_miss_rate']}%  — KG found nothing to traverse)")
    print()
    print(f"  All questions      : {summary['retrieval_accuracy_all']}%")
    print(f"  Entity questions   : {summary['retrieval_accuracy_entity_q']}%")
    print(f"  Descriptive        : {summary['retrieval_accuracy_descriptive_q']}%")
    print(f"  Seeded only        : {summary['retrieval_accuracy_seeded']}%  "
          f"(excl. seed misses — upper bound)")
    print()
    print("  ── SECONDARY: IR ranking metrics ────────────────────────")
    print(f"  Hit@{K} (entity) : {summary['Hit_at_K_entity']}%")
    print(f"  Hit@1  (entity) : {summary['Hit_at_1_entity']}%")
    print(f"  MRR    (entity) : {summary['MRR_entity']}%")
    print()
    print(f"  Avg latency (this run): {summary['avg_latency_ms_this_run']} ms")
    print("=" * 70)

    return summary


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    run_kg_retrieval_evaluation()
