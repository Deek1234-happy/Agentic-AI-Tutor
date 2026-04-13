# debug_rag.py
import requests
import json

BASE_URL = "http://localhost:8000"

def debug_rag():
    print("🔍 Debugging RAG endpoint...")
    
    # Test with a simple question
    response = requests.post(
        f"{BASE_URL}/rag/",
        json={
            "question": "What is artificial intelligence?",
            "top_k": 3
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 500:
        # Check if the server logs show more details
        print("\n⚠️ Check your FastAPI server logs for the full error traceback")

if __name__ == "__main__":
    debug_rag()