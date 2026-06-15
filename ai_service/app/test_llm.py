# test_llm.py
import sys
import os
sys.path.append("D:/Graduation_Project/Agentic-AI-Tutor/ai_service/app")
from llm import test_groq_connection

print("Testing Groq connection...")
result = test_groq_connection()
print(f"Result: {result}")