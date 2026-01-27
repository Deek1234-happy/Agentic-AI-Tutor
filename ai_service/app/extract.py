from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .router import validate_file, validate_file_type, route_file
from .text_cleaner import clean_text

router = APIRouter()

class FilePayload(BaseModel):
    file_id: str
    file_path: str
    file_type: str

@router.post("/")
def extract_file(payload: FilePayload):
    try:
        validate_file(payload.file_path)
        validate_file_type(payload.file_type)

        raw_text = route_file(
            payload.file_path,
            payload.file_type
        )

        cleaned_text = clean_text(raw_text)
        
        return {
            "file_id": payload.file_id,
            "status": "completed",
            "text": cleaned_text
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
