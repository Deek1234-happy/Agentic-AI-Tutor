# app/chat_service.py

from uuid import UUID
from sqlalchemy import text

from .db import SessionLocal
from .embedding import embed_texts
from .vector_store import search_similar_chunks
from .rag_service import build_context, IDK_MESSAGE
from .llm import generate_answer
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
# Save Message
# ============================================================

def save_chat_message(session_id: UUID, role: str, content: str):
    db = SessionLocal()
    try:
        result = db.execute(text("""
            INSERT INTO rag.chat_messages (session_id, role, content)
            VALUES (:session_id, :role, :content)
            RETURNING id
        """), {
            "session_id": str(session_id),
            "role": role,
            "content": content
        })
        message_id = result.fetchone()[0]
        db.commit()
        return message_id
    finally:
        db.close()


# ============================================================
# Save Citations
# ============================================================

def save_citations(message_id, chunk_ids):
    db = SessionLocal()
    try:
        for chunk_id in chunk_ids:
            db.execute(text("""
                INSERT INTO rag.chat_citations (message_id, chunk_id)
                VALUES (:message_id, :chunk_id)
            """), {
                "message_id": str(message_id),
                "chunk_id": str(chunk_id)
            })
        db.commit()
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
        rewritten = generate_answer(prompt, temperature=0)
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
        result = generate_answer(prompt, temperature=0).strip().upper()
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
        response = generate_answer(
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
        response = generate_answer(
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
        raw = generate_answer(prompt, temperature=0)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return {"intent": "needs_answer", "reply": ""}

# ============================================================
# MAIN CHAT LOGIC 
# ============================================================

def handle_chat(payload):
   

    if not session_exists(payload.session_id):
        return {"answer": IDK_MESSAGE, "citations": []}
    
    # 1️⃣ Classify intent first
    intent_result = classify_intent_llm(payload.question)

    # 2️⃣ If only greeting → return immediately
    if intent_result["intent"] == "greeting_only":
        return {
            "answer": intent_result["reply"],  # polite greeting
            "citations": []
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
            top_k=payload.top_k
        )

        print(f"Retrieved {len(results)} chunks (before filtering)")

        # Apply similarity threshold
        filtered = [r for r in results if r[5] >= SIMILARITY_THRESHOLD]

        print(f"Kept {len(filtered)} chunks (score >= {SIMILARITY_THRESHOLD})")

        for r in filtered:
            print(f"  → Doc: {r[1]} | Pages: {r[3]}-{r[4]} | Score: {r[5]}")

        all_retrieved.extend(filtered)

    if not all_retrieved:
        print("\nNo chunks passed similarity threshold.")
        return {"answer": IDK_MESSAGE, "citations": []}

    # ============================
    # Deduplicate + Final Threshold Safety
    # ============================

    unique = {}
    for r in all_retrieved:
        unique[r[0]] = r

    retrieved = list(unique.values())

    # Safety threshold re-check
    retrieved = [r for r in retrieved if r[5] >= SIMILARITY_THRESHOLD]

    retrieved = sorted(retrieved, key=lambda x: x[5], reverse=True)[:5]

    if not retrieved:
        print("\nAll chunks removed after threshold filtering.")
        return {"answer": IDK_MESSAGE, "citations": []}

    context = build_context(retrieved)

    # ============================
    # Final synthesis
    # ============================

    prompt = f"""
You are an academic tutor.

Your task is to provide a clear, detailed explanation as if teaching a student.

IMPORTANT RULES:
- Use ONLY the information contained in the CONTEXT.
- You may reorganize, combine, summarize, and clarify ideas from the context.
- You may explain relationships between ideas that are explicitly supported by the context.
- Do NOT introduce new concepts, examples, or facts not present in the context.
- Answer the QUESTION in the **same language as it is asked**.
- If the message starts with a greeting and you are also prepending a greeting, do NOT repeat the greeting at the beginning of your answer."
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

    answer = generate_answer(prompt, temperature=0.1)
    # Prepend greeting if needed
    if prepend_greeting:
        answer = prepend_greeting + answer

    print("\n=== RAW MODEL OUTPUT ===")
    print(answer)
    print("========================")

    print("\n=== FINAL RETRIEVED CHUNKS USED ===")
    for r in retrieved:
        print(f"Document: {r[1]}")
        print(f"Pages: {r[3]} - {r[4]}")
        print(f"Score: {r[5]}")
        print(r[2][:500])
        print("------")

    if not answer or IDK_MESSAGE.lower() in answer.lower():
        return {"answer": IDK_MESSAGE, "citations": []}

    # 7️ Save conversation
    save_chat_message(payload.session_id, "user", payload.question)
    message_id = save_chat_message(payload.session_id, "assistant", answer)

    chunk_ids = [r[0] for r in retrieved]
    save_citations(message_id, chunk_ids)

    citations = [
        {
            "document_id": str(r[1]),
            "page_start": r[3],
            "page_end": r[4]
        }
        for r in retrieved
    ]

    return {
        "answer": answer,
        "citations": citations
    }
