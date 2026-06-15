"""
KG Retrieval Evaluation — Natural Questions, Triples+Text
=========================================================

This evaluates the paper's KG-GraphRAG (Triplets+Text) setting:
retrieved evidence is the graph triples plus the source chunk text attached
to each retrieved relationship.

Important: old KG edges will not have source_text. Rebuild the KG after the
kg_extractor/kg_store changes so this evaluator can use the associated text.
"""

from app.evaluation import nq_kg_retrieve as base


RESULTS_FILE = "data/kg_retrieval_results_triples_text.json"
METRICS_FILE = "data/kg_retrieval_metrics_triples_text.json"


def build_context_blob(subgraph: dict) -> str:
    parts = []
    seen_text = set()

    for rel in subgraph.get("relationships", []):
        parts.append(
            f"{rel.get('source', '')} "
            f"{rel.get('relation', '')} "
            f"{rel.get('target', '')}"
        )

        source_text = (rel.get("source_text") or "").strip()
        if source_text and source_text not in seen_text:
            seen_text.add(source_text)
            parts.append(source_text)

    return base.normalize_text(" ".join(parts))


def retrieval_accuracy_hit(subgraph: dict, gold_answers: list) -> bool:
    blob = build_context_blob(subgraph)
    for ans in gold_answers:
        norm_ans = base.normalize_text(ans)
        if norm_ans and norm_ans in blob:
            return True
    return False


def call_kg_retrieval(question: str, document_id: str) -> dict:
    response = base.requests.post(
        base.KG_QUERY_URL,
        json={
            "question": question,
            "subject_id": base.SUBJECT_ID,
            "user_id": base.USER_ID,
            "document_ids": [document_id],
            "hops": base.HOPS,
            "flexible_seed_match": True,
            "include_source_text": True,
            "use_llm_query_entities": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    base.RESULTS_FILE = RESULTS_FILE
    base.METRICS_FILE = METRICS_FILE
    base.CONTEXT_MODE = "triples_text"
    base.build_context_blob = build_context_blob
    base.retrieval_accuracy_hit = retrieval_accuracy_hit
    base.call_kg_retrieval = call_kg_retrieval
    base.run_kg_retrieval_evaluation()
