# app/chat_service.py

from uuid import UUID
from sqlalchemy import text

from .db import SessionLocal
from .embedding import embed_texts
from .vector_store import search_similar_chunks
from .rag_service import build_context, IDK_MESSAGE
from .llm import generate_chat_answer
from collections import defaultdict
import re
import os
import json


SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.5))

# ============================================================
# Session Validation
# ============================================================

def session_exists(session_id: UUID):
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT 1
            FROM rag.chat_sessions
            WHERE id = :session_id
        """), {
            "session_id": str(session_id)
        })
        return result.fetchone() is not None
    finally:
        db.close()


# ============================================================
# Get Last N Messages
# ============================================================

def get_chat_history(session_id: UUID, limit: int = 10):
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT role, content
            FROM rag.chat_messages
            WHERE session_id = :session_id
            ORDER BY created_at DESC
            LIMIT :limit
        """), {
            "session_id": str(session_id),
            "limit": limit
        })
        rows = result.fetchall()
        return list(reversed(rows))
    finally:
        db.close()

# ============================================================
# EXISTING REWRITE RULES
# ============================================================

REWRITE_RULES = """
You rewrite follow-up questions into fully standalone search queries.

Rules:
- Use conversation history to resolve pronouns (it, its, they, this, that, etc.)
- Keep the user's language (answer in the same language as the original question)
- Keep the user's language
- Do NOT add new facts
- Do NOT explain
- Return ONLY the rewritten standalone query
"""

def rewrite_query(latest_question: str, chat_history):

    if not chat_history:
        return latest_question

    history_text = ""
    for role, content in chat_history:
        role_name = "User" if role == "user" else "Assistant"
        history_text += f"{role_name}: {content}\n"

    prompt = f"""
{REWRITE_RULES}

Conversation:
{history_text}

Latest question:
{latest_question}

Standalone rewritten query:
"""

    try:
        rewritten = generate_chat_answer(prompt, temperature=0)
        return rewritten.strip() if rewritten else latest_question
    except Exception:
        return latest_question


# ============================================================
# NEW: HISTORY DEPENDENCY CLASSIFIER
# ============================================================

HISTORY_DEPENDENCY_PROMPT = """
You are analyzing whether a user question depends on previous conversation context.

Answer ONLY with:
DEPENDENT
or
INDEPENDENT

DEPENDENT → The question refers to previous discussion or requires earlier context.
INDEPENDENT → The question can be understood without previous messages.

Conversation history:
{history}

Question:
{question} 
"""

def classify_history_dependency(question: str, history):

    if not history:
        return "INDEPENDENT"

    history_text = ""
    for role, content in history:
        role_name = "User" if role == "user" else "Assistant"
        history_text += f"{role_name}: {content}\n"

    prompt = HISTORY_DEPENDENCY_PROMPT.format(
        history=history_text,
        question=question
    )

    try:
        result = generate_chat_answer(prompt, temperature=0).strip().upper()
        if "DEPENDENT" in result:
            return "DEPENDENT"
        return "INDEPENDENT"
    except Exception:
        return "INDEPENDENT"


# ============================================================
# REASONING RULES
# ============================================================

REASONING_RULES = """
Analyze the question.

Tasks:
1. Resolve pronouns inside the same sentence (e.g., "its" refers to closest noun).
2. Normalize wording for clarity.
3. Do NOT add new facts.
4. Return a cleaned standalone question only.
5. Keep the language of the original question (answer in the same language)
"""

def analyze_reasoning(question: str):

    prompt = f"""
{REASONING_RULES}

Question:
{question}

Result:
"""

    try:
        result = generate_answer(prompt, temperature=0)
        return result.strip() if result else question
    except Exception:
        return question


# ============================================================
# COMPLEXITY CLASSIFIER
# ============================================================

COMPLEXITY_PROMPT = """
Classify the question as:

SIMPLE → single fact lookup or direct retrieval
COMPLEX → requires multiple reasoning steps or multiple concepts

Answer only with SIMPLE or COMPLEX.

QUESTION:
{question}
"""

def classify_complexity(question: str) -> str:
    try:
        response = generate_chat_answer(
            COMPLEXITY_PROMPT.format(question=question),
            temperature=0
        ).strip().upper()

        if "COMPLEX" in response:
            return "COMPLEX"

        return "SIMPLE"

    except Exception:
        return "SIMPLE"


# ============================================================
# DECOMPOSITION
# ============================================================

DECOMPOSE_PROMPT = """
Break the following question into minimal independent sub-questions.

Return as numbered list.
Do not answer the question.

QUESTION:
{question}
"""

def decompose_question(question: str):
    try:
        response = generate_chat_answer(
            DECOMPOSE_PROMPT.format(question=question),
            temperature=0
        )

        lines = response.split("\n")
        sub_questions = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = re.match(r"^\d+\.\s*(.+)", line)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) > 5:
                    sub_questions.append(candidate)

        if not sub_questions:
            return [question]

        return sub_questions

    except Exception:
        return [question]


def classify_intent_llm(message: str) -> dict:
    prompt = f"""
You are an intent classifier.

Classify the user's message into ONE of:

1) greeting_only → only greeting / small talk
2) greeting_with_question → greeting + real question
3) needs_answer → real question without greeting

Return STRICT JSON:

{{
  "intent": "greeting_only" OR "greeting_with_question" OR "needs_answer",
  "reply": if greeting_only → short polite greeting (1 sentence),
           if greeting_with_question → short polite greeting (1 sentence),
           if needs_answer → ""
}}

Rules:
- Be flexible. Any greeting counts.
- If message is only a greeting, the reply must include a short polite greeting **AND a helping sentence** in the same language.
- greeting + question = greeting_with_question
- Detect the language of the user message.
- Return the greeting reply in the **same language** as the detected message.
- Output JSON only.

User message:
{message}

JSON:
"""

    try:
        raw = generate_chat_answer(prompt, temperature=0)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return {"intent": "needs_answer", "reply": ""}


# ============================================================
# KG RETRIEVAL HELPER  (non-blocking — never breaks RAG flow)
# ============================================================

def _try_kg_retrieval(
    question:             str,
    session_id:           str,
    user_id:              str,
    allowed_document_ids: list,
) -> dict:
    """
    Attempt a session-aware, subject-scoped KG retrieval.

    Uses the session_id to resolve the subject automatically from
    the existing rag.chat_documents + content.documents tables.

    Returns answer + structured KG context. On any error, returns
    an empty KG payload and IDK_MESSAGE.
    """
    empty_kg = {"entities": [], "relationships": []}
    try:
        from .kg_service import (
            retrieve_subgraph_for_session,
            focus_subgraph_for_query,
            subgraph_to_kg_context,
            generate_kg_answer,
        )

        subgraph = retrieve_subgraph_for_session(
            question=question,
            session_id=str(session_id),
            user_id=str(user_id),
            allowed_document_ids=[str(d) for d in allowed_document_ids],
        )

        focused = focus_subgraph_for_query(subgraph, question)
        kg_context = subgraph_to_kg_context(focused)
        kg_answer = generate_kg_answer(question=question, subgraph=focused)

        print(f"\n[Chat] KG answer preview: {kg_answer[:200]}")
        return {
            "answer": kg_answer,
            "kg_context": kg_context,
            "entities_used": len(kg_context["entities"]),
            "relations_used": len(kg_context["relationships"]),
        }

    except Exception as exc:
        print(f"[Chat] KG retrieval failed (non-fatal): {exc}")
        return {
            "answer": IDK_MESSAGE,
            "kg_context": empty_kg,
            "entities_used": 0,
            "relations_used": 0,
        }


# ============================================================
# MAIN CHAT LOGIC
# ============================================================

def handle_chat(payload):
    empty_kg = {"entities": [], "relationships": []}

    if not session_exists(payload.session_id):
        return {
            "answer": IDK_MESSAGE,
            "confidence_score": 0.0,
            "citations": [],
            "kg_context": empty_kg,
            "entities_used": 0,
            "relations_used": 0,
        }

    # 1️⃣ Classify intent first
    intent_result = classify_intent_llm(payload.question)

    # 2️⃣ If only greeting → return immediately
    if intent_result["intent"] == "greeting_only":
        return {
            "answer": intent_result["reply"],
            "confidence_score": 0.0,
            "citations": [],
            "kg_context": empty_kg,
            "entities_used": 0,
            "relations_used": 0,
        }

    # 3️⃣ If greeting + question → save greeting to prepend later
    prepend_greeting = ""
    if intent_result["intent"] == "greeting_with_question":
        prepend_greeting = intent_result["reply"] + " "


    history = get_chat_history(payload.session_id)

    # decide if history should be used
    dependency = classify_history_dependency(payload.question, history)

    if dependency == "DEPENDENT":
        rewritten_query = rewrite_query(payload.question, history)
    else:
        rewritten_query = payload.question

    cleaned_query = analyze_reasoning(rewritten_query)

    complexity = classify_complexity(cleaned_query)

    if complexity == "COMPLEX":
        sub_questions = decompose_question(cleaned_query)
    else:
        sub_questions = [cleaned_query]

    # ============================
    # DEBUG — REASONING PIPELINE
    # ============================

    print("\n==============================")
    print("DEBUG — REASONING PIPELINE")
    print("==============================")
    print(f"Original Question: {payload.question}")
    print(f"History Dependency: {dependency}")
    print(f"Rewritten (history-aware): {rewritten_query}")
    print(f"Cleaned (intra-query): {cleaned_query}")
    print(f"Complexity: {complexity}")
    print("Sub-Questions:")
    for i, sq in enumerate(sub_questions, 1):
        print(f"  {i}. {sq}")
    print("==============================\n")

    # ============================
    # Retrieval with Threshold
    # ============================

    all_retrieved = []

    for i, sq in enumerate(sub_questions, 1):

        print(f"\n--- Retrieving for Sub-Question {i} ---")
        print(f"Query: {sq}")

        embedding = embed_texts([sq])[0]

        results = search_similar_chunks(
            query_embedding=embedding,
            allowed_document_ids=payload.allowed_document_ids,
            user_id=payload.user_id,
            top_k=payload.top_k
        )

        print(f"Retrieved {len(results)} chunks (before filtering)")

        filtered = [r for r in results if r[5] >= SIMILARITY_THRESHOLD]

        print(f"Kept {len(filtered)} chunks (score >= {SIMILARITY_THRESHOLD})")

        for r in filtered:
            print(f"  → Doc: {r[1]} | Pages: {r[3]}-{r[4]} | Score: {r[5]}")

        all_retrieved.extend(filtered)

    # ============================
    # Deduplicate + Final Threshold Safety
    # ============================

    unique = {}
    for r in all_retrieved:
        unique[r[0]] = r

    retrieved = list(unique.values())
    retrieved = [r for r in retrieved if r[5] >= SIMILARITY_THRESHOLD]
    retrieved = sorted(retrieved, key=lambda x: x[5], reverse=True)[:5]

    # ============================
    # RAG Answer  (original, unchanged)
    # ============================

    rag_answer = IDK_MESSAGE

    if retrieved:
        context = build_context(retrieved)

        rag_prompt = f"""
You are an academic tutor.

Your task is to provide a clear, detailed explanation as if teaching a student.

IMPORTANT RULES:
- Use ONLY the information contained in the CONTEXT.
- You may reorganize, combine, summarize, and clarify ideas from the context.
- You may explain relationships between ideas that are explicitly supported by the context.
- Do NOT introduce new concepts, examples, or facts not present in the context.
- Answer the QUESTION in the **same language as it is asked**.
- If the message starts with a greeting and you are also prepending a greeting, do NOT repeat the greeting at the beginning of your answer.
- If the context does not provide enough information, say exactly:
"{IDK_MESSAGE}"

Write the explanation in a structured and educational style.
Use paragraphs and clear transitions.

CONTEXT:
{context}

QUESTION:
{payload.question}

EXPLANATION:
"""
        try:
            rag_answer = generate_chat_answer(rag_prompt, temperature=0.1)
            rag_answer = rag_answer.strip() if rag_answer else IDK_MESSAGE
        except Exception:
            rag_answer = IDK_MESSAGE

        print("\n=== RAG ANSWER ===")
        print(rag_answer[:300])
        print("==================")

        print("\n=== FINAL RETRIEVED CHUNKS USED ===")
        for r in retrieved:
            print(f"Document: {r[1]}")
            print(f"Pages: {r[3]} - {r[4]}")
            print(f"Score: {r[5]}")
            print(r[2][:500])
            print("------")

    else:
        print("\nNo chunks passed similarity threshold — skipping RAG answer.")

    # ============================
    # KG Answer  (session-aware, subject-scoped)
    # ============================

    kg_result = _try_kg_retrieval(
        question=payload.question,
        session_id=payload.session_id,
        user_id=payload.user_id,
        allowed_document_ids=payload.allowed_document_ids,
    )
    kg_answer = kg_result["answer"]

    # ============================
    # Hybrid Fusion
    # ============================

    try:
        from .kg_service import fuse_answers
        final_answer = fuse_answers(
            question=payload.question,
            rag_answer=rag_answer,
            kg_answer=kg_answer,
        )
    except Exception as exc:
        print(f"[Chat] Fusion failed, falling back to RAG answer: {exc}")
        final_answer = rag_answer

    print("\n=== HYBRID FINAL ANSWER ===")
    print(final_answer[:300])
    print("===========================")

    # Prepend greeting if needed
    if prepend_greeting:
        final_answer = prepend_greeting + final_answer

    # Guard: both sources returned IDK
    if not final_answer or IDK_MESSAGE.lower() in final_answer.lower():
        return {
            "answer": IDK_MESSAGE,
            "confidence_score": 0.0,
            "citations": [],
            "kg_context": kg_result["kg_context"],
            "entities_used": kg_result["entities_used"],
            "relations_used": kg_result["relations_used"],
        }

    confidence_score = 0.0

    citations = [
        {
            "document_id": str(r[1]),
            "chunk_id":    str(r[0]),
            "page_start":  r[3],
            "page_end":    r[4],
        }
        for r in retrieved
    ]

    return {
        "answer":           final_answer,
        "confidence_score": confidence_score,
        "citations":        citations,
        "kg_context":       kg_result["kg_context"],
        "entities_used":    kg_result["entities_used"],
        "relations_used":   kg_result["relations_used"],
    }