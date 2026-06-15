import math
import os

from ..embedding import embed_texts
from ..rag_service import IDK_MESSAGE, build_context
from ..vector_store import search_similar_chunks
#from .ragas_eval import evaluate_ragas

from ..llm import generate_answer
from ..chat_service import (
    SIMILARITY_THRESHOLD, analyze_reasoning, classify_complexity,
    classify_history_dependency, classify_intent_llm, decompose_question,
    get_chat_history, handle_chat, rewrite_query, session_exists
)
import json
import cohere
import re
import math

# ══════════════════════════════════════════════════════════════
# PAYLOAD WRAPPER
# ══════════════════════════════════════════════════════════════

class PayloadWrapper:
    def __init__(self, data: dict):
        self.question               = data.get("question")
        self.session_id             = data.get("session_id")
        self.user_id                = data.get("user_id")
        self.subject_id             = data.get("subject_id")
        self.allowed_document_ids   = data.get("allowed_document_ids", [])
        self.top_k                  = data.get("top_k", 5)


# ══════════════════════════════════════════════════════════════
# 1. SYSTEMS  (each runs exactly once per evaluation)
# ══════════════════════════════════════════════════════════════

def llm_only(question: str) -> str:
    """Baseline: pure LLM, no retrieval."""
    return generate_answer(question)


def rag_only(payload) -> dict:
    """RAG pipeline — returns {answer, contexts}."""

    if not session_exists(payload.session_id):
        pass  # dataset questions have no session history — that's fine

    intent_result = classify_intent_llm(payload.question)

    if intent_result["intent"] == "greeting_only":
        return {"answer": intent_result["reply"], "contexts": []}

    prepend_greeting = ""
    if intent_result["intent"] == "greeting_with_question":
        prepend_greeting = intent_result["reply"] + " "

    history    = get_chat_history(payload.session_id)
    dependency = classify_history_dependency(payload.question, history)

    rewritten_query = (
        rewrite_query(payload.question, history)
        if dependency == "DEPENDENT"
        else payload.question
    )

    cleaned_query = analyze_reasoning(rewritten_query)
    complexity    = classify_complexity(cleaned_query)
    sub_questions = decompose_question(cleaned_query) if complexity == "COMPLEX" else [cleaned_query]

    # ── Retrieval ──────────────────────────────────────────────
    all_retrieved = []
    for sq in sub_questions:
        embedding = embed_texts([sq])[0]
        results   = search_similar_chunks(
            query_embedding=embedding,
            allowed_document_ids=payload.allowed_document_ids,
            user_id=payload.user_id,
            top_k=payload.top_k,
        )
        all_retrieved.extend([r for r in results if r[5] >= SIMILARITY_THRESHOLD])

    # ── Deduplicate & rank ─────────────────────────────────────
    unique    = {r[0]: r for r in all_retrieved}
    retrieved = sorted(unique.values(), key=lambda x: x[5], reverse=True)[:5]

    # ── Generate answer ────────────────────────────────────────
    if not retrieved:
        return {"answer": IDK_MESSAGE, "contexts": []}

    context = build_context(retrieved)
    rag_prompt = f"""You are an academic tutor.

Your task is to provide a clear, detailed explanation as if teaching a student.

IMPORTANT RULES:
- Use ONLY the information contained in the CONTEXT.
- Do NOT introduce new facts.
- Answer in the same language.

CONTEXT:
{context}

QUESTION:
{payload.question}

EXPLANATION:
"""
    try:
        rag_answer = generate_answer(rag_prompt, temperature=0.1)
        rag_answer = rag_answer.strip() if rag_answer else IDK_MESSAGE
    except Exception:
        rag_answer = IDK_MESSAGE

    # FIX: use r[2] consistently (same field as extract_rag_context)
    return {
        "answer":   rag_answer,
        "contexts": [r[2] for r in retrieved],
    }


# ══════════════════════════════════════════════════════════════
# 2. CONTEXT EXTRACTORS
# ══════════════════════════════════════════════════════════════

def _clean_contexts(raw_texts: list, max_per_context=400, min_len=50, limit=3) -> list:
    """Shared helper: deduplicate, filter noise, trim."""
    seen    = set()
    cleaned = []
    for text in raw_texts:
        if not isinstance(text, str):
            continue
        text = text.strip().replace("OCR PAGE TEXT", "")
        if len(text) < min_len:
            continue
        # Normalise whitespace for dedup key
        key = re.sub(r"\s+", " ", text).lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text[:max_per_context])
        if len(cleaned) >= limit:
            break
    return cleaned


def extract_rag_context(payload) -> list:
    """Return clean RAG context chunks for RAGAS evaluation."""
    embedding = embed_texts([payload.question])[0]
    results   = search_similar_chunks(
        query_embedding=embedding,
        allowed_document_ids=payload.allowed_document_ids,
        user_id=payload.user_id,
        top_k=payload.top_k,
    )

    filtered = [r for r in results if r[5] >= SIMILARITY_THRESHOLD]
    if not filtered:
        filtered = results[:3]  # fallback: take top-3 regardless of threshold

    raw_texts = [r[2] for r in filtered]  # FIX: unified to r[2]
    contexts  = _clean_contexts(raw_texts)

    print("\n===== RAG CONTEXTS =====")
    for c in contexts:
        print(type(c), "->", c[:120])

    return contexts


def extract_kg_context(payload) -> list:
    from ..kg_service import retrieve_subgraph_for_subject, retrieve_subgraph_for_session, format_subgraph_as_text

    # ── لو عندنا subject_id مباشرة → نتجنب مشكلة الـ session ──
    if getattr(payload, "subject_id", None):
        print(f"[KG] Using subject_id directly: {payload.subject_id[:8]}")
        subgraph = retrieve_subgraph_for_subject(
            question=payload.question,
            subject_id=payload.subject_id,
            user_id=payload.user_id,
            document_ids=(
                [str(d) for d in payload.allowed_document_ids]
                if payload.allowed_document_ids else None
            ),
            hops=2,
            flexible_seed_match=True,  # مهم عشان يلاقي entities بشكل أوسع
        )
    else:
        # fallback للـ session-based (للـ chat العادي)
        print(f"⚠️  No subject_id — falling back to session lookup (may return empty)")
        subgraph = retrieve_subgraph_for_session(
            question=payload.question,
            session_id=payload.session_id,
            user_id=payload.user_id,
            allowed_document_ids=payload.allowed_document_ids or [],
            hops=2,
        )

    # ── Debug ──────────────────────────────────────────────────
    print(f"[KG] entities={len(subgraph['entities'])}  rels={len(subgraph['relationships'])}")

    if not subgraph["entities"] and not subgraph["relationships"]:
        print("⚠️  KG returned empty subgraph.")
        return []

    kg_text = format_subgraph_as_text(subgraph)
    return [str(kg_text)] if kg_text.strip() else []


# ══════════════════════════════════════════════════════════════
# 3. JUDGE  (Cohere)
# ══════════════════════════════════════════════════════════════

# NOTE: keep your API key in an environment variable, not hardcoded.
co = cohere.ClientV2(os.getenv("COHERE_API_KEY", ""))


def judge_with_cohere(question: str, answers: dict) -> dict:
    """Score all three answers with Cohere as an impartial judge."""

    prompt = f"""
You are a STRICT and CRITICAL evaluator.

Your job is to evaluate answers objectively and carefully.

========================
QUESTION:
{question}
========================

ANSWER 1 (LLM):
{answers['llm']}

ANSWER 2 (RAG):
{answers['rag']}

ANSWER 3 (KG+RAG):
{answers['kg_rag']}

========================
EVALUATION CRITERIA (score each from 0 to 10):

1. Correctness   – factually correct? deduct for wrong/unverifiable claims.
2. Relevance     – directly addresses the question?
3. Faithfulness  – consistent with known facts? penalise hallucinations.
4. Groundedness  – supported by retrieved evidence?
                   LLM (no retrieval) must NOT get high groundedness scores.
                   RAG/KG+RAG score high ONLY if they use context correctly.
5. Completeness  – fully answers all aspects?
6. Reasoning     – logically coherent?

========================
STRICT SCORING RULES:
- 9–10 are RARE; most good answers sit at 6–8.
- DO NOT give all three answers the same scores.
- Penalise generic, ungrounded, or hallucinated answers.

========================
OUTPUT FORMAT — STRICT JSON ONLY, no markdown fences:

{{
  "LLM":    {{"correctness":0,"relevance":0,"faithfulness":0,"groundedness":0,"completeness":0,"reasoning":0}},
  "RAG":    {{"correctness":0,"relevance":0,"faithfulness":0,"groundedness":0,"completeness":0,"reasoning":0}},
  "KG+RAG": {{"correctness":0,"relevance":0,"faithfulness":0,"groundedness":0,"completeness":0,"reasoning":0}}
}}
"""
    try:
        response = co.chat(
            model="command-a-reasoning-08-2025",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        text = "".join(
            item.text for item in response.message.content
            if hasattr(item, "text") and item.text
        ).strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())

        return {"error": "Invalid JSON", "raw_output": text}

    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════
# 4. MAIN PIPELINE  (FIX: run systems ONCE, score in all modes)
# ══════════════════════════════════════════════════════════════

def _clean_scores(d: dict) -> dict:
    """Replace NaN / Inf floats with 0.0 so JSON serialisation never fails."""
    return {
        k: (0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
        for k, v in d.items()
    }


def run_systems(payload) -> dict:
    """
    Execute LLM-only, RAG-only, and KG+RAG exactly once and return a bundle
    that every scoring mode can share.  This eliminates the 3× redundant calls.
    """
    llm_ans    = llm_only(payload.question)
    rag_result = rag_only(payload)
    rag_ans    = rag_result["answer"]
    kg_ans     = handle_chat(payload)["answer"]

    # ── Contexts for RAGAS ────────────────────────────────────
    rag_contexts = extract_rag_context(payload)

    kg_only_contexts = extract_kg_context(payload)
    if kg_only_contexts:
        # Merge RAG + KG contexts, deduplicate
        combined = rag_contexts + kg_only_contexts
        seen, kg_contexts = set(), []
        for c in combined:
            key = re.sub(r"\s+", " ", c).lower()
            if key not in seen:
                seen.add(key)
                kg_contexts.append(c)
    else:
        # FIX: don't silently inflate KG scores with RAG contexts
        print("⚠️  KG has no unique context — kg_contexts will equal rag_contexts.")
        kg_contexts = rag_contexts  # still need something for RAGAS to run

    print("\n===== DEBUG CONTEXTS =====")
    for c in rag_contexts[:5]:
        print("RAG  |", type(c), "->", str(c)[:200])
    for c in kg_contexts[:5]:
        print("KG   |", type(c), "->", str(c)[:200])

    return {
        "question":     payload.question,
        "answers":      {"llm": llm_ans, "rag": rag_ans, "kg_rag": kg_ans},
        "rag_contexts": rag_contexts,
        "kg_contexts":  kg_contexts,
    }


def evaluate(payload, ground_truth=None, mode="all"):
    """
    Evaluate one question.

    Parameters
    ----------
    mode : "ragas" | "judge" | "cheap" | "all"
        "all"   → run every scorer and merge results into one dict  ← recommended
        "ragas" → RAGAS metrics only
        "judge" → Cohere judge only
        "cheap" → answers only, no scoring
    """
    if isinstance(payload, dict):
        payload = PayloadWrapper(payload)

    # ── Run systems once ──────────────────────────────────────
    bundle = run_systems(payload)
    question     = bundle["question"]
    answers      = bundle["answers"]
    rag_contexts = bundle["rag_contexts"]
    kg_contexts  = bundle["kg_contexts"]

    result = {
        "question": question,
        "answers":  answers,
    }

    # ── RAGAS scoring ─────────────────────────────────────────
    if mode in ("ragas", "all"):
        ragas_llm = _clean_scores(
            evaluate_ragas(question, answers["llm"], [""], ground_truth=ground_truth)
        )
        ragas_rag = _clean_scores(
            evaluate_ragas(question, answers["rag"], rag_contexts, ground_truth=ground_truth)
        )
        ragas_kg  = _clean_scores(
            evaluate_ragas(question, answers["kg_rag"], kg_contexts, ground_truth=ground_truth)
        )
        result["ragas"] = {
            "llm":    ragas_llm,
            "rag":    ragas_rag,
            "kg_rag": ragas_kg,
        }

    # ── Cohere judge scoring ───────────────────────────────────
    if mode in ("judge", "all"):
        result["judge"] = judge_with_cohere(question, answers)

    # "cheap" or "all" already has answers — nothing extra needed
    return result


# ══════════════════════════════════════════════════════════════
# 5. LOGGING
# ══════════════════════════════════════════════════════════════

def save_result(result: dict):
    with open("evaluation_logs.json", "a") as f:
        f.write(json.dumps(result) + "\n")

