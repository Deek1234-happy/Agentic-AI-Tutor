from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union

from .router import validate_file, validate_file_type, route_file
from .text_cleaner import clean_text
from .chunker import chunk_text
from .embedding import embed_texts, EMBEDDING_VERSION, embed_query
from .vector_store import VectorStore
from .answer_generator import generate_answer


router = APIRouter()

# Initialize Vector Store 
VECTOR_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2 output dimension
vector_store = VectorStore(VECTOR_DIM)

# Request / Response Models

class FilePayload(BaseModel):
    file_id: str
    file_path: str
    file_type: str


class ChunkResponse(BaseModel):
    file_id: str
    chunk_id: str
    source_type: str
    page_or_slide: Optional[Union[str, List[str]]]
    section: Optional[Union[str, List[str]]]
    text: str


class EmbeddedChunkResponse(BaseModel):
    file_id: str
    chunk_id: str
    source_type: str
    page_or_slide: Optional[Union[str, List[str]]]
    section: Optional[Union[str, List[str]]]
    text: str
    embedding: List[float]
    embedding_version: str


# Extraction + Chunking Endpoint

@router.post("/", response_model=List[ChunkResponse])
def extract_and_chunk_file(payload: FilePayload):
    try:
        validate_file(payload.file_path)
        validate_file_type(payload.file_type)

        raw_text = route_file(payload.file_path, payload.file_type)
        if not raw_text.strip():
            raise ValueError("Extracted text is empty")

        cleaned_text = clean_text(raw_text)

        chunks = chunk_text(
            text=cleaned_text,
            file_id=payload.file_id,
            source_type=payload.file_type
        )

        return chunks

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# Extraction + Chunking + Embedding Endpoint

@router.post("/embed", response_model=List[EmbeddedChunkResponse])
def extract_chunk_and_embed(payload: FilePayload):
    """
    Extract → clean → chunk → embed → store in vector store.
    """
    try:
        validate_file(payload.file_path)
        validate_file_type(payload.file_type)

        # Extract & clean
        raw_text = route_file(payload.file_path, payload.file_type)
        cleaned_text = clean_text(raw_text)

        # Chunking
        chunks = chunk_text(
            text=cleaned_text,
            file_id=payload.file_id,
            source_type=payload.file_type
        )

        # Embedding
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embed_texts(texts)

        for chunk, vector in zip(chunks, embeddings):
            chunk["embedding"] = vector
            chunk["embedding_version"] = EMBEDDING_VERSION

        # Add to Vector Store for search
        vector_store.add(embeddings, chunks)

        return chunks

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# Query Endpoint 

class QueryPayload(BaseModel):
    query: str
    top_k: Optional[int] = 5

@router.post("/query")
def query_vector_store(payload: QueryPayload):
    """
    Query → embedding → FAISS → LLM answer
    """
    try:
        # Embed query
        query_emb = embed_query(payload.query)
        if not query_emb:
            raise ValueError("Failed to generate query embedding")

        # Search vector store
        results = vector_store.search(query_emb, top_k=payload.top_k)

        if not results:
            return {
                "query": payload.query,
                "answer": "No relevant information found in the document.",
                "sources": []
            }

        # Extract chunk texts
        contexts = [r["metadata"]["text"] for r in results]

        # Generate answer from LLM
        answer = generate_answer(payload.query, contexts)

        return {
            "query": payload.query,
            "answer": answer,
            "sources": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
