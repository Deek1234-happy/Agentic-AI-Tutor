from fastapi import FastAPI
from .extract import router as extract_router

app = FastAPI(title="AI File Processing Service")

app.include_router(extract_router, prefix="/extract")
