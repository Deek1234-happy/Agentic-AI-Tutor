# app/main.py
from fastapi import FastAPI
from .extract import router as extract_router
from .search import router as search_router
from .rag import router as rag_router



app = FastAPI(
    title="AI File Processing Service",
    version="1.0.0"
)

app.include_router(
    extract_router,
    prefix="/extract",
    tags=["Extraction & Chunking"]
)

app.include_router(
    search_router,
    prefix="/search",
    tags=["Semantic Search"]
)

app.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG QA"]
)