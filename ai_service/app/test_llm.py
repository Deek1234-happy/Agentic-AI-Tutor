import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "phi3:mini",
        "prompt": "Explain zero-day attack in one sentence.",
        "stream": False
    }
)

print(response.json())
