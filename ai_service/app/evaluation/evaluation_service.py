from ..llm import generate_answer
from ..chat_service import handle_chat
import json


class PayloadWrapper:
    def __init__(self, data: dict):
        self.question = data.get("question")
        self.session_id = data.get("session_id")
        self.user_id = data.get("user_id")
        self.allowed_document_ids = data.get("allowed_document_ids", [])
        self.top_k = data.get("top_k", 5)

# =========================
# 1. SYSTEMS
# =========================


# for evaluation , we want to test the LLM's ability to answer questions without any retrieval or KG information, to see how it performs with just the question alone. 
# This will help us understand the baseline performance of the LLM and how much it relies on 
# external info to answer questions accurately.
def llm_only(question: str):
    return generate_answer(question)


# This function will be used to test the LLM's ability 
# to answer questions based on the question alone, 
# without any retrieval or KG information.
def kg_rag(payload):
    result = handle_chat(payload)
    return result["answer"]


# not accurate untill now 
def rag_only(payload):
    result = handle_chat(payload)
    return result["answer"] 



# =========================
# 2. EVALUATION (LLM Judge)
# =========================

def judge(question, answers):
    prompt = f"""
You are an expert evaluator.

Question: {question}

LLM: {answers['llm']}
RAG: {answers['rag']}
KG+RAG: {answers['kg_rag']}

Evaluate based on:
- correctness
- completeness
- reasoning
- groundedness

Return JSON:
{{
 "best": "...",
 "scores": {{
   "LLM": ...,
   "RAG": ...,
   "KG+RAG": ...
 }},
 "reason": "..."
}}
"""
    return generate_answer(prompt)



# =========================
# 3. PIPELINE
# =========================

def evaluate(payload):

    if isinstance(payload, dict):
        payload = PayloadWrapper(payload)
   
    question = payload.question

    #question = payload.question

    # 1. run systems
    llm_ans = llm_only(question)
    rag_ans = rag_only(payload)
    kg_ans = kg_rag(payload)

    answers = {
        "llm": llm_ans,
        "rag": rag_ans,
        "kg_rag": kg_ans
    }

    # 2. judge
    evaluation = judge(question, answers)

    return {
        "question": question,
        "answers": answers,
        "evaluation": evaluation
    }



# =========================
# 4. LOGGING
# =========================

def save_result(result):
    with open("evaluation_logs.json", "a") as f:
        f.write(json.dumps(result) + "\n")

