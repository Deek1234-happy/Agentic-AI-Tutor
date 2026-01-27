from fastapi import FastAPI
from .extract import router as extract_router

app = FastAPI(
    title="AI File Processing Service",
    version="1.0.0"
)

app.include_router(
    extract_router,
    prefix="/extract",
    tags=["Extraction & Chunking"]
)
