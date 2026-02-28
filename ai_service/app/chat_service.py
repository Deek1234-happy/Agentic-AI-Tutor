# # app/chat_service.py

# from uuid import UUID
# from sqlalchemy import text

# from .db import SessionLocal
# from .embedding import embed_texts
# from .vector_store import search_similar_chunks
# from .rag_service import build_context, IDK_MESSAGE
# from .llm import generate_answer


# # ===============================
# # Session Validation
# # ===============================

# def session_exists(session_id: UUID):
#     db = SessionLocal()
#     try:
#         result = db.execute(text("""
#             SELECT 1
#             FROM rag.chat_sessions
#             WHERE id = :session_id
#         """), {
#             "session_id": str(session_id)
#         })

#         return result.fetchone() is not None

#     finally:
#         db.close()


# # ===============================
# # Get Last N Messages (Correct Order)
# # ===============================

# def get_chat_history(session_id: UUID, limit: int = 10):
#     db = SessionLocal()
#     try:
#         result = db.execute(text("""
#             SELECT role, content
#             FROM rag.chat_messages
#             WHERE session_id = :session_id
#             ORDER BY created_at DESC
#             LIMIT :limit
#         """), {
#             "session_id": str(session_id),
#             "limit": limit
#         })

#         rows = result.fetchall()

#         # Reverse to chronological order (oldest → newest)
#         return list(reversed(rows))

#     finally:
#         db.close()


# # ===============================
# # Save Message
# # ===============================

# def save_chat_message(session_id: UUID, role: str, content: str):
#     db = SessionLocal()
#     try:
#         result = db.execute(text("""
#             INSERT INTO rag.chat_messages (session_id, role, content)
#             VALUES (:session_id, :role, :content)
#             RETURNING id
#         """), {
#             "session_id": str(session_id),
#             "role": role,
#             "content": content
#         })

#         message_id = result.fetchone()[0]
#         db.commit()

#         return message_id

#     finally:
#         db.close()


# # ===============================
# # Save Citations
# # ===============================

# def save_citations(message_id, chunk_ids):
#     db = SessionLocal()
#     try:
#         for chunk_id in chunk_ids:
#             db.execute(text("""
#                 INSERT INTO rag.chat_citations (message_id, chunk_id)
#                 VALUES (:message_id, :chunk_id)
#             """), {
#                 "message_id": str(message_id),
#                 "chunk_id": str(chunk_id)
#             })

#         db.commit()

#     finally:
#         db.close()


# # ===============================
# # Main Chat Logic
# # ===============================

# def handle_chat(payload):

#     # 1️⃣ Validate session
#     if not session_exists(payload.session_id):
#         return {"answer": IDK_MESSAGE, "citations": []}

#     # 2️⃣ Retrieve previous conversation history (BEFORE saving new question)
#     history = get_chat_history(payload.session_id)

#     history_text = ""
#     for role, content in history:
#         history_text += f"{role.upper()}: {content}\n"

#     # 3️⃣ Embed current question
#     query_embedding = embed_texts([payload.question])[0]

#     # 4️⃣ Retrieve relevant chunks
#     retrieved = search_similar_chunks(
#         query_embedding=query_embedding,
#         top_k=payload.top_k
#     )

#     retrieved = [r for r in retrieved if r[5] >= 0]

#     if not retrieved:
#         return {"answer": IDK_MESSAGE, "citations": []}

#     context = build_context(retrieved)

#     # 5️⃣ Build prompt
#     prompt = f"""
# You are an academic tutor.

# Use ONLY the provided CONTEXT.
# Use conversation history for continuity.

# CONVERSATION HISTORY:
# {history_text}

# DOCUMENT CONTEXT:
# {context}

# QUESTION:
# {payload.question}

# If insufficient context, reply exactly:
# "{IDK_MESSAGE}"

# EXPLANATION:
# """

#     # 6️⃣ Generate answer
#     answer = generate_answer(prompt)

#     if not answer or IDK_MESSAGE.lower() in answer.lower():
#         return {"answer": IDK_MESSAGE, "citations": []}

#     # 7️⃣ Save user message AFTER prompt building
#     save_chat_message(payload.session_id, "user", payload.question)

#     # 8️⃣ Save assistant message
#     message_id = save_chat_message(payload.session_id, "assistant", answer)

#     # 9️⃣ Save citations
#     chunk_ids = [r[0] for r in retrieved]
#     save_citations(message_id, chunk_ids)

#     # 🔟 Prepare response
#     citations = [
#         {
#             "document_id": str(r[1]),
#             "page_start": r[3],
#             "page_end": r[4]
#         }
#         for r in retrieved
#     ]

#     return {
#         "answer": answer,
#         "citations": citations
#     }

# app/chat_service.py
# app/chat_service.py

from uuid import UUID
from sqlalchemy import text

from .db import SessionLocal
from .embedding import embed_texts
from .vector_store import search_similar_chunks
from .rag_service import build_context, IDK_MESSAGE
from .llm import generate_answer


# ===============================
# Session Validation
# ===============================

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


# ===============================
# Get Last N Messages
# ===============================

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
        return list(reversed(rows))  # chronological order

    finally:
        db.close()


# ===============================
# Save Message
# ===============================

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


# ===============================
# Save Citations
# ===============================

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


# ===============================
# Query Rewrite (LLM-powered)
# ===============================

REWRITE_RULES = """
You rewrite follow-up questions into fully standalone search queries.

Rules:
- Use conversation history to resolve pronouns (it, its, they, this, that, etc.)
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


# ===============================
# Main Chat Logic
# ===============================

def handle_chat(payload):

    # 1️⃣ Validate session
    if not session_exists(payload.session_id):
        return {"answer": IDK_MESSAGE, "citations": []}

    # 2️⃣ Get conversation history
    history = get_chat_history(payload.session_id)

    history_text = ""
    for role, content in history:
        history_text += f"{role.upper()}: {content}\n"

    # 3️⃣ Rewrite query (for better retrieval)
    rewritten_query = rewrite_query(
        payload.question,
        history
    )

    # 4️⃣ Embed rewritten query
    query_embedding = embed_texts([rewritten_query])[0]

    # 5️⃣ Retrieve relevant chunks
    retrieved = search_similar_chunks(
        query_embedding=query_embedding,
        top_k=payload.top_k
    )

    retrieved = [r for r in retrieved if r[5] >= 0.5]

    if not retrieved:
        return {"answer": IDK_MESSAGE, "citations": []}

    context = build_context(retrieved)

    # 6️⃣ Build final RAG prompt
    prompt = f"""
You are an academic tutor.

Use ONLY the provided CONTEXT.
Use conversation history for continuity.

CONVERSATION HISTORY:
{history_text}

DOCUMENT CONTEXT:
{context}

QUESTION:
{payload.question}

If insufficient context, reply exactly:
"{IDK_MESSAGE}"

EXPLANATION:
"""

    answer = generate_answer(prompt, temperature=0.1)

    if not answer or IDK_MESSAGE.lower() in answer.lower():
        return {"answer": IDK_MESSAGE, "citations": []}

    # 7️⃣ Save user message
    save_chat_message(payload.session_id, "user", payload.question)

    # 8️⃣ Save assistant message
    message_id = save_chat_message(payload.session_id, "assistant", answer)

    # 9️⃣ Save citations
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