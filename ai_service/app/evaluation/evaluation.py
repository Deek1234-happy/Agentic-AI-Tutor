
from fastapi import APIRouter
from .evaluation_service import evaluate


router = APIRouter()

@router.post("/evaluate")
def evaluate_endpoint(payload: dict):
    result = evaluate(payload)
    return result