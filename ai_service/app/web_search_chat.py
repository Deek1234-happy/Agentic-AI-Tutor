from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import UUID
from typing import Literal
import os

from .chat_service import (
    get_chat_history,
    classify_history_dependency,
    rewrite_query
)

from .web_search_service import run_web_search


router = APIRouter()


class WebSearchRequest(BaseModel):
    session_id: UUID
    question: str
    language: Literal["en", "kn", "hi", "ml", "ta", "te"] = "en"


@router.post("", summary="Web search chat")
def web_search_chat(payload: WebSearchRequest):
    if not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Web search is not configured. Add TAVILY_API_KEY to ai_service/.env and restart the AI service.",
        )

    try:

        #  get conversation history
        history = get_chat_history(payload.session_id)

        # check if question depends on history
        dependency = classify_history_dependency(
            payload.question,
            history
        )

        # rewrite if needed
        if dependency == "DEPENDENT":
            final_query = rewrite_query(payload.question, history)
        else:
            final_query = payload.question

        print("\n=== WEB SEARCH QUERY ===")
        print(final_query)
        print("========================\n")

        # send query + original user question (for language control) to n8n workflow
        result = run_web_search(final_query, payload.question, payload.language)

        print("\n=== FINAL RESULT ===")
        print(result)

        return result

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Web search provider failed: {e}") from e