from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def groq_judge(question, answer, contexts):

    context_text = "\n".join(contexts)

    prompt = f"""
You are an expert evaluator for AI-generated answers in a Retrieval-Augmented Generation (RAG) system.

Your task is to evaluate the quality of the answer using the question and the retrieved context.

Question:
{question}

Retrieved Context:
{context_text}

Generated Answer:
{answer}

Evaluate the answer using the following criteria:

1. Faithfulness – Is the answer supported by the retrieved context?
2. Relevance – Does the answer directly address the question?
3. Completeness – Does the answer sufficiently cover the topic?
4. Hallucination – Does the answer contain information not supported by the context?
5. Clarity – Is the explanation clear and logically structured?

Based on these criteria, give a final reliability score between 0 and 1.

Scoring guideline:
0.0 – Completely incorrect or unrelated
0.3 – Mostly incorrect or hallucinated
0.5 – Partially correct but incomplete
0.7 – Mostly correct and relevant
0.9 – Highly reliable and well supported
1.0 – Perfect answer fully supported by context

Return ONLY a number between 0 and 1.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    score = float(response.choices[0].message.content.strip())

    return score