# app/llm.py
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"


def generate_answer(prompt: str) -> str:
    """
    Generate answer using local Ollama Mistral model.
    """

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1  # Lower temperature for stricter, more deterministic responses
        },
        timeout=300
    )

    if response.status_code != 200:
        raise Exception(f"Ollama error: {response.text}")

    result = response.json()

    return result.get("response", "").strip()
