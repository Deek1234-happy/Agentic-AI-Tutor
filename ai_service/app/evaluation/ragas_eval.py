# from ragas import evaluate
# from ragas.metrics import faithfulness, answer_relevancy
# from ragas.metrics import context_precision, context_recall
# from ragas.llms import LangchainLLMWrapper
# from ragas.embeddings import LangchainEmbeddingsWrapper
# from datasets import Dataset
# from langchain_openai import ChatOpenAI
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_core.outputs import LLMResult
# import math
# import os
# from langchain_cohere import ChatCohere


# #── Groq-safe LLM: forces n=1 on every call ───────────────────────────────────
# class GroqChatOpenAI(ChatOpenAI):
#     def _create_chat_result(self, response, generation_info=None):
#         return super()._create_chat_result(response, generation_info)

#     @property
#     def _default_params(self):
#         params = super()._default_params
#         params["n"] = 1          # Groq only allows n=1
#         params.pop("n", None)    # belt-and-suspenders: remove if RAGAS re-adds it
#         return params

#     def _generate(self, messages, stop=None, run_manager=None, **kwargs):
#         kwargs["n"] = 1          # force on every generate call too
#         return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

#     async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
#         kwargs["n"] = 1
#         return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)


# # ── LLM + Embeddings setup ────────────────────────────────────────────────────
# _chat = GroqChatOpenAI(
#     model="llama-3.3-70b-versatile",
#     #model="llama3-8b-8192",
#     #model="mixtral-8x7b-32768",
#     openai_api_key=os.getenv("GROQ_API_KEY"),
#     openai_api_base="https://api.groq.com/openai/v1",
#     n=1,
# )
# ragas_llm = LangchainLLMWrapper(_chat)

# _embeddings = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )
# ragas_embeddings = LangchainEmbeddingsWrapper(_embeddings)

# # # ── LLM (Cohere) ──────────────────────────────────────────────────────────────
# # _chat = ChatCohere(
# #     model="command-a-reasoning-08-2025",
# #     cohere_api_key=os.getenv("COHERE_API_KEY"),
# #     max_tokens=4096
# # )
# # ragas_llm = LangchainLLMWrapper(_chat)

# # # ── Embeddings (HuggingFace local — no API key needed) ────────────────────────
# # _embeddings = HuggingFaceEmbeddings(
# #     model_name="sentence-transformers/all-MiniLM-L6-v2"
# # )
# # ragas_embeddings = LangchainEmbeddingsWrapper(_embeddings)

# # ── Inject into metrics ───────────────────────────────────────────────────────
# faithfulness.llm             = ragas_llm
# answer_relevancy.llm         = ragas_llm
# answer_relevancy.embeddings  = ragas_embeddings
# context_precision.llm        = ragas_llm
# context_recall.llm           = ragas_llm


# # ── Main evaluation function ──────────────────────────────────────────────────
# def evaluate_ragas(question: str, answer: str, contexts: list, ground_truth: str = None) -> dict:
#     clean_contexts = []
#     for c in contexts:
#         if isinstance(c, str):
#             c = c.strip().replace("OCR PAGE TEXT", "")
#             if c:
#                 clean_contexts.append(c[:500])

#     clean_contexts = clean_contexts[:2]

#     if not clean_contexts:
#         clean_contexts = [""]

#     print("\n===== RAGAS INPUT =====")
#     print("Question:", question)
#     print("Answer:", answer[:200])
#     print("Contexts:", clean_contexts)

#     data = {
#         "question": [question],
#         "answer":   [answer],
#         "contexts": [clean_contexts],
#     }

#     if ground_truth:
#         data["ground_truth"] = [ground_truth]
#         metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
#     else:
#         metrics = [faithfulness, answer_relevancy]

#     dataset = Dataset.from_dict(data)

#     try:
#         result = evaluate(
#             dataset,
#             metrics=metrics,
#             llm=ragas_llm,
#             embeddings=ragas_embeddings,
#         )
#         output = result.to_pandas().iloc[0].to_dict()

#         for k, v in output.items():
#             if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
#                 output[k] = 0.0

#         return output

#     except Exception as e:
#         print("RAGAS ERROR:", e)
#         return {
#             "faithfulness":     0.0,
#             "answer_relevancy": 0.0,
#         }