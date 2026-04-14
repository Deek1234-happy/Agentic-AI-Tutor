# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from contextlib import asynccontextmanager
import logging
import os
from .extract import router as extract_router
from .chunk_kg import router as chunk_kg_router
from .search import router as search_router
from .rag import router as rag_router
from .web_search_chat import router as web_search_router
from .chat import router as chat_router
from .kg import router as kg_router
from .kg_db import init_kg_schema
from .voice import router as voice_router
from .vstt import router as vstt_router
from .vtts import router as vtts_route
#from .evaluation.evaluation_service import evaluate
from app.evaluation import evaluation


# ============================================================
# Lifespan — initialise Neo4j schema once at startup
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_kg_schema()
    except Exception as exc:
        # Non-fatal: app runs even if Neo4j is temporarily unavailable
        print(f"[Startup] KG schema init failed (non-fatal): {exc}")
    yield


# ============================================================
# App
# ============================================================

app = FastAPI(
    title="AI File Processing Service",
    version="2.0.0",
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    extract_router,
    prefix="/extract",
    tags=["Extraction & Chunking"]
)

app.include_router(
    chunk_kg_router,
    prefix="/chunk",
    tags=["Chunking & Knowledge Graph"]
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

app.include_router(
    chat_router,
    prefix="/chat",
    tags=["Context-Aware Chat"]
)

# Voice chat — imported here to match the original structure
app.include_router(
    voice_router,
    prefix="/voice",
    tags=["Voice Chat"]
)

#  STT Endpoint
app.include_router(
    vstt_router,
    prefix="/audio",
    tags=["Speech-to-Text"]
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(
    vtts_route,
    prefix="/audio",
    tags=["Text-to-Speech"]
)

app.include_router(
    web_search_router,
    prefix="/web-search",
    tags=["Web Search"]
)

# ── Knowledge Graph ───────────────────────────────────────────
app.include_router(
    kg_router,
    prefix="/kg",
    tags=["Knowledge Graph"]
)


# ── Evaluation ───────────────────────────────────────────────



app.include_router(evaluation.router)