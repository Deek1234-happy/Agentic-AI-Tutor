# app/rag_service.py
from typing import List, Tuple

from .embedding import embed_texts
from .vector_store import search_similar_chunks
from .llm import generate_answer
from .reranker import rerank_chunks

# Single source of truth
IDK_MESSAGE = "I don't know."


def build_context(chunks: List[Tuple], max_chars: int = 6000) -> str:
    """
    Build context string from retrieved chunks.

    Expected tuple format:
    (id, document_id, chunk_text, page_start, page_end, score)
    """

    context_parts = []
    total_chars = 0

    for chunk in chunks:
        text = chunk[2]

        if not text or not text.strip():
            continue

        text = text.strip()

        if total_chars + len(text) + 2 > max_chars:
            remaining = max_chars - total_chars - 10
            if remaining > 100:
                text = text[:remaining].rstrip() + "..."
            else:
                break

        context_parts.append(text)
        total_chars += len(text) + 2

    return "\n\n".join(context_parts)


# def _verify_answer_in_context(answer: str, context: str) -> bool:
    answer = answer.lower()
    context = context.lower()

    if "don't know" in answer:
        return True

    answer_words = [w for w in answer.split() if len(w) > 4]

    if not answer_words:
        return False

    matches = sum(1 for w in answer_words if w in context)

    return (matches / len(answer_words)) >= 0.3


def answer_question(question: str, top_k: int = 5):
    """
    Strict RAG behavior:
    - Uses ONLY DB chunks
    - Returns IDK if not grounded
    - Prints retrieved chunks with scores
    """

    # 1️⃣ Embed question
    #query_embedding = embed_texts([question])[0]
    query_embedding = embed_texts([question], is_query=True)[0] #for eval .

    # 2️⃣ Retrieve from DB
    retrieved_chunks = search_similar_chunks(
        query_embedding=query_embedding,
        top_k=10
    )

    # 3️⃣ Filter weak matches
    retrieved_chunks = [
        r for r in retrieved_chunks
        if r[5] >= 0.5
    ]

    if not retrieved_chunks:
        return IDK_MESSAGE, []

    # 4️⃣ Re-rank
    retrieved_chunks = rerank_chunks(
        question=question,
        chunks=retrieved_chunks,
        top_k=top_k
    )
    
    

    # 4️⃣ Build context
    context = build_context(retrieved_chunks)

    if not context or len(context.strip()) < 20:
        return IDK_MESSAGE, retrieved_chunks

    # 5️⃣ Prompt
    prompt = f"""You are a precise question-answering assistant.

Answer the question using ONLY the information in the CONTEXT below.
Give a SHORT and DIRECT answer — no explanation, no extra detail.

RULES:
Answer in as few words as possible (ideally 1-5 words)
Do NOT explain your reasoning
Do NOT repeat the question
If the answer is not in the CONTEXT, reply exactly with: "{IDK_MESSAGE}"

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""
    
#     """
# You are an academic tutor.

# Your task is to EXPLAIN the concept clearly as if teaching a student.

# IMPORTANT RULES:
# - Use ONLY the information found in the CONTEXT.
# - You may reorganize, combine, and simplify the information.
# - Do NOT add external knowledge.
# - If the CONTEXT does not contain enough information, reply exactly with: "{IDK_MESSAGE}"

# CONTEXT:
# {context}

# QUESTION:
# {question}

# EXPLANATION:
# """

    try:
        answer = generate_answer(prompt)
    except Exception:
        return IDK_MESSAGE, retrieved_chunks

    answer = answer.strip() if answer else ""

    # print("\n=== RAW MODEL OUTPUT ===")
    # print(answer)
    # print("======")

    # print("\n=== RETRIEVED CHUNKS ===")
    # for r in retrieved_chunks:
    #     print(f"Document: {r[1]}")
    #     print(f"Pages: {r[3]} - {r[4]}")
    #     print(f"Score: {r[5]}")
    #     print(r[2][:500])
    #     print("------")

    if not answer:
        return IDK_MESSAGE, retrieved_chunks

    answer_lower = answer.lower()
    if (IDK_MESSAGE.lower() in answer_lower or "don't know" in answer_lower) and len(answer.strip()) < 50:
        return IDK_MESSAGE, retrieved_chunks

    # if not _verify_answer_in_context(answer, context):
    #     return IDK_MESSAGE, retrieved_chunks

    return answer, retrieved_chunks
