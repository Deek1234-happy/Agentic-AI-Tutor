import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"


def generate_answer(query: str, contexts: list[str]) -> str:
    """
    Generate a clean answer using Ollama (local LLM)
    """

    context_text = "\n\n".join(contexts)

    prompt = f"""
You are a helpful assistant.
Answer the question ONLY using the context below.
If the answer is not in the context, say: "I couldn't find the answer in the document."

Context:
{context_text}

Question:
{query}

Answer clearly and concisely:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()
    return response.json()["response"].strip()
