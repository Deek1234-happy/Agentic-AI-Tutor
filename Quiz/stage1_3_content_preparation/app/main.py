# app/main.py
from fastapi import FastAPI
from .quiz import router as quiz_chunking_router

app = FastAPI(
    title="AI File Processing Service (Quiz Chunking)",
    version="1.0.0"
)

app.include_router(
    quiz_chunking_router,
    prefix="/quiz",
    tags=["Quiz Chunking"]
)