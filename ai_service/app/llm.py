# # app/llm.py
# import requests

# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL_NAME = "mistral"


# def generate_answer(prompt: str) -> str:
#     """
#     Generate answer using local Ollama Mistral model.
#     """

#     response = requests.post(
#         OLLAMA_URL,
#         json={
#             "model": MODEL_NAME,
#             "prompt": prompt,
#             "stream": False,
#             "temperature": 0.1  # Lower temperature for stricter, more deterministic responses
#         },
#         timeout=300
#     )

#     if response.status_code != 200:
#         raise Exception(f"Ollama error: {response.text}")

#     result = response.json()

#     return result.get("response", "").strip()




# app/llm.py

import os
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ===============================
# LLM Provider Configuration
# ===============================

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3-70b-8192")


# ===============================
# Generic LLM Completion
# ===============================

def generate_answer(prompt: str, temperature: float = 0.1) -> str:
    """
    Generic LLM completion function.
    Works with Groq (OpenAI-compatible API).
    You can switch providers without changing function name.
    """

    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set in environment variables")

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        LLM_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"LLM error: {response.text}")

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()