# 🧠 Agentic AI Tutor — AI Service

> **Branch:** `AI`  
> **Role:** Python AI/ML microservice — the intelligence layer of the Agentic AI Tutor platform  
> **Tech Stack:** FastAPI · PostgreSQL (pgvector) · Neo4j · Sentence Transformers · Groq LLM · Piper TTS · Faster-Whisper STT

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Module Reference](#module-reference)
- [API Endpoints](#api-endpoints)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Installation](#installation)
- [Running the Service](#running-the-service)
- [Evaluation Suite](#evaluation-suite)
- [Project Structure](#project-structure)

---

## Overview

The AI service is a self-contained FastAPI application that provides all AI capabilities consumed by the ASP.NET Core backend. It handles the full document intelligence pipeline:

1. **Document Ingestion** — parse PDFs, PPTX, DOCX, TXT, CSV, and images (with OCR) into clean text
2. **Semantic Chunking** — split text using adaptive similarity-based boundary detection
3. **Embedding & Vector Storage** — embed chunks with `intfloat/e5-base-v2` and store in PostgreSQL via pgvector
4. **Knowledge Graph Construction** — extract entities and domain-specific relationships into Neo4j
5. **Retrieval-Augmented Generation** — hybrid BM25 + dense retrieval, cross-encoder reranking, then LLM answer synthesis with citations
6. **Context-Aware Chat** — multi-turn conversation with per-session history and source citations
7. **Voice Interface** — full speech-to-text (Faster-Whisper) and text-to-speech (Piper TTS) pipelines
8. **Web Search Chat** — fallback to live web search via an n8n webhook when documents don't contain the answer
9. **MCQ Generation** — Bloom-taxonomy-aware quiz chunk processing and LLM-based MCQ generation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                                                                  │
│  /extract  /chunk  /search  /rag  /chat  /voice  /audio         │
│  /web-search  /kg  /quiz  /evaluation                           │
└──────────┬──────────────────────────────────────┬───────────────┘
           │                                      │
     ┌─────▼──────┐                     ┌─────────▼──────────┐
     │ PostgreSQL  │                     │       Neo4j         │
     │ (pgvector)  │                     │  Knowledge Graph    │
     │ chunks +    │                     │  Entities &         │
     │ embeddings  │                     │  Relationships      │
     └─────────────┘                     └────────────────────┘
           │
     ┌─────▼──────────────────────────────────────────────┐
     │  AI Models                                          │
     │  • intfloat/e5-base-v2          (embedding)         │
     │  • BAAI/bge-reranker-base       (reranking)         │
     │  • all-MiniLM-L6-v2             (chunking)          │
     │  • Groq API (llama-3.1-8b)      (LLM generation)    │
     │  • Piper TTS (en_US-amy-medium) (speech synthesis)  │
     │  • Faster-Whisper (medium)      (transcription)     │
     └────────────────────────────────────────────────────┘
```

### Document Processing Pipeline

```
Upload File
    │
    ▼
extract.py ── PyMuPDF / python-docx / python-pptx / Tesseract OCR
    │               (PDF, DOCX, PPTX, TXT, CSV, Images)
    ▼
text_cleaner.py ── Normalize, deduplicate, language detection
    │
    ▼
chunker.py ── Adaptive semantic chunking (all-MiniLM-L6-v2)
    │          similarity_threshold=0.72, dynamic breakpoints
    ▼
embedding.py ── e5-base-v2 ("passage: <text>")
    │
    ▼
vector_store.py ── pgvector INSERT with embedding + metadata
```

### RAG Query Pipeline

```
User Question
    │
    ▼
embed_texts() ── e5-base-v2 ("query: <question>")
    │
    ▼
search.py ── Hybrid: dense (cosine sim pgvector) + BM25 (rank_bm25)
    │         Filter by user_id + document_ids
    ▼
reranker.py ── BAAI/bge-reranker-base cross-encoder scoring
    │           Final score = reranker_score (retrieval score as tiebreaker)
    ▼
rag_service.py ── Build context string with source citations
    │
    ▼
llm.py ── Groq API (llama-3.1-8b-instant) with fallback chain
    │      Auto-retry on rate-limit, model fallback on token-limit
    ▼
Response: { answer, citations: [{ document_id, page_start, page_end }] }
```

### Knowledge Graph Pipeline

```
Document Chunks
    │
    ▼
kg_extractor.py ── LLM-based NER + relation extraction
    │               Domain detection (CS / medical / physics / etc.)
    │               FORBIDDEN generic relations enforced via prompt
    ▼
kg_service.py ── Build intra-doc + cross-doc graph
    │
    ▼
kg_db.py / kg_store.py ── Store in Neo4j (entities + typed relationships)
    │
    ▼
kg_service.py (retrieval) ── Subgraph retrieval → context string → LLM answer
```

### MCQ Generation Pipeline

```
Backend sends quiz_chunks (with bloom_level, chunk_type, concepts)
    │
    ▼
quiz_prompt_builder.py ── Build per-slot model prompts
    │
    ▼
quiz_slot_selector.py ── Smart selection maximising Bloom + chunk diversity
    │
    ▼
quiz_generator.py ── LLM generates MCQs (question + 4 options + explanation)
    │
    ▼
Response: { mcqs[], requested_count, available_slots, generated_count }
```

---

## Module Reference

| Module | Responsibility |
|--------|---------------|
| `main.py` | FastAPI app factory, CORS, router registration, Neo4j schema init |
| `extract.py` | Multi-format file parsing (PDF/DOCX/PPTX/TXT/CSV/images) |
| `parsers.py` | File-type-specific text extraction helpers |
| `text_cleaner.py` | Text normalization, language detection, deduplication |
| `chunker.py` | Adaptive semantic chunker (configurable similarity threshold) |
| `embedding.py` | Sentence-transformer embedding with e5-style query/passage prefixing |
| `vector_store.py` | pgvector similarity search with user/document filtering |
| `search.py` | Hybrid BM25 + dense retrieval router |
| `reranker.py` | Cross-encoder reranking with BAAI/bge-reranker-base |
| `rag.py` / `rag_service.py` | Single-turn RAG Q&A with citations |
| `chat.py` / `chat_service.py` | Multi-turn chat with session history |
| `llm.py` | LLM client with retry logic, rate-limit handling, model fallback chain |
| `kg.py` | Knowledge graph API routes |
| `kg_extractor.py` | LLM-based entity + relation extraction |
| `kg_service.py` | KG build, cross-doc linking, subgraph retrieval, KG-based Q&A |
| `kg_db.py` / `kg_store.py` | Neo4j CRUD operations |
| `kg_pipeline.py` | End-to-end KG ingestion orchestrator |
| `kg_chunking_strategy.py` | KG-specific chunking configuration |
| `db.py` | SQLAlchemy engine + session factory (reads `DATABASE_URL` from `.env`) |
| `voice.py` | Voice chat endpoint (STT → RAG → TTS) |
| `audio/tts.py` | Piper TTS (offline ONNX, English + Arabic models) |
| `audio/stt.py` | Faster-Whisper transcription (CPU/GPU via `WHISPER_DEVICE`) |
| `audio/hybrid_tts.py` | Multi-backend TTS with Coqui/XTTS fallback |
| `web_search_chat.py` | Web-search-augmented chat via n8n webhook |
| `web_search_service.py` | n8n webhook HTTP client |
| `quiz/quiz_router.py` | `/quiz/process` — chunk a document for quiz generation |
| `quiz/quiz_generate_router.py` | `/quiz/generate` — generate MCQs from processed chunks |
| `quiz/quiz_prompt_builder.py` | Build per-slot LLM prompts (Bloom + chunk_type aware) |
| `quiz/quiz_slot_selector.py` | Diversity-aware slot selection algorithm |
| `quiz/quiz_generator.py` | LLM inference for MCQ generation |
| `quiz/quiz_cleaner.py` | Post-process and validate LLM MCQ output |
| `quiz/quiz_metadata.py` | Bloom taxonomy metadata assignment |
| `evaluation/` | RAGAS, TruLens, NQ/HotpotQA evaluation scripts |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/extract/embed` | Upload a file → extract, chunk, embed, store in pgvector |
| `POST` | `/chunk/` | Extract text + build KG chunks (for Knowledge Graph) |
| `POST` | `/search/` | Semantic search against stored chunks |
| `POST` | `/rag/` | Single-turn RAG Q&A with citations |
| `POST` | `/chat/` | Multi-turn context-aware chat |
| `POST` | `/voice/ask-audio` | Voice input → RAG answer → voice output |
| `POST` | `/audio/stt` | Speech-to-text transcription |
| `POST` | `/audio/tts` | Text-to-speech synthesis |
| `POST` | `/web-search` | Web-search-augmented Q&A |
| `POST` | `/kg/build` | Build knowledge graph from a document |
| `GET`  | `/kg/document/{id}` | Retrieve document subgraph |
| `DELETE` | `/kg/document/{id}` | Remove document from KG |
| `POST` | `/quiz/process` | Process document chunks for quiz generation |
| `POST` | `/quiz/generate` | Generate MCQs from processed chunks |
| `GET`  | `/evaluation/` | Run RAGAS evaluation |

Interactive docs: `http://localhost:8000/docs`

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | 3.11 recommended |
| PostgreSQL | 14+ | With **pgvector** extension |
| Neo4j | 4.x / 5.x | For knowledge graph features |
| Tesseract OCR | 4.x | For scanned PDF / image text extraction |
| Poppler | latest | For `pdf2image` (PDF page rendering) |
| n8n | latest | Optional — only for web-search chat feature |

**Hardware note:** The default model stack runs on CPU. For GPU inference, set `WHISPER_DEVICE=cuda` (requires CUDA 12 + cuDNN).

---

## Environment Variables

Create a `.env` file inside the `ai_service/` directory:

```env
# ── Database ─────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname?sslmode=require

# ── LLM (Groq API) ───────────────────────────────────────────────────────
LLM_API_KEY=your_groq_api_key_here
LLM_URL=https://api.groq.com/openai/v1/chat/completions
LLM_MODEL=llama-3.1-8b-instant

# ── Neo4j ────────────────────────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ── Voice / Whisper ──────────────────────────────────────────────────────
WHISPER_DEVICE=cpu            # or "cuda" for GPU
WHISPER_COMPUTE_TYPE=int8     # "float16" for GPU

# ── Web Search (n8n) ─────────────────────────────────────────────────────
N8N_WEBHOOK_URL=http://localhost:5678/webhook/web-search

# ── RAG Retrieval ────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD=0.5
```

---

## Installation

### 1. Clone the repository and switch to the correct branch

```bash
git clone https://github.com/Rehab-Hamdy/Agentic-AI-Tutor.git
cd Agentic-AI-Tutor
git checkout AI
cd ai_service
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install system dependencies

**Ubuntu / Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils ffmpeg libsndfile1
```

**macOS (Homebrew):**
```bash
brew install tesseract poppler ffmpeg
```

**Windows:**
- Install [Tesseract](https://github.com/tesseract-ocr/tesseract) and add it to `PATH`
- Install [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Note on torch:** The `requirements.txt` pins `torch==2.1.2` for TTS compatibility. If you're on a machine without the matching CUDA toolkit, install the CPU variant first:
> ```bash
> pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### 5. Set up PostgreSQL with pgvector

```sql
-- Connect to your PostgreSQL instance
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the required schemas
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS rag;

-- The backend's EF Core migrations handle table creation.
-- Alternatively, the chunking endpoints create tables on first use.
```

### 6. Set up Neo4j (for Knowledge Graph features)

```bash
# Option A: Docker
docker run \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:5

# Option B: Neo4j Desktop
# Download from https://neo4j.com/download/
```

### 7. Create the `.env` file

Copy and fill in the template from the [Environment Variables](#environment-variables) section.

### 8. Create the static directory

```bash
mkdir -p static/audio
```

---

## Running the Service

```bash
# From inside ai_service/
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at:
- **API Base URL:** `http://localhost:8000`
- **Interactive Docs (Swagger):** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Exposing the service to the backend (ngrok)

The ASP.NET Core backend communicates with this service over HTTP. For local development, expose the service with ngrok:

```bash
ngrok http 8000
```

Copy the generated HTTPS URL and set it as `AIService.BaseURL` in the backend's `appsettings.json`.

---

## Feature Setup Guides

This section walks you through configuring and using each major feature of the AI service from scratch.

---

### 🔍 Feature 1: RAG (Retrieval-Augmented Generation)

RAG is the core feature — it answers questions from uploaded documents with exact citations.

**What you need:**
- PostgreSQL running with `pgvector` extension
- A valid `LLM_API_KEY` (Groq) in your `.env`
- The `DATABASE_URL` in your `.env` pointing to your database

**Step 1 — Verify pgvector is installed**

```sql
-- Connect to your PostgreSQL database
\c AgenticAITutor
CREATE EXTENSION IF NOT EXISTS vector;

-- Confirm it's active
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Step 2 — Upload and embed a document**

```bash
curl -X POST http://localhost:8000/extract/embed \
  -F "file=@/path/to/your/lecture.pdf" \
  -F "document_id=<UUID-from-backend>" \
  -F "user_id=<user-UUID>"
```

The service will:
1. Parse the PDF (PyMuPDF + Tesseract for scanned pages)
2. Clean and semantically chunk the text
3. Embed every chunk with `intfloat/e5-base-v2`
4. Store chunks and embeddings in `content.document_chunks`

**Step 3 — Ask a question**

```bash
curl -X POST http://localhost:8000/rag/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the difference between supervised and unsupervised learning?",
    "top_k": 5
  }'
```

Response:
```json
{
  "answer": "Supervised learning uses labeled data...",
  "citations": [
    { "document_id": "uuid", "page_start": 3, "page_end": 4 }
  ]
}
```

**Tuning retrieval quality:**

Edit `.env` to adjust the similarity threshold (default `0.5`):
```env
SIMILARITY_THRESHOLD=0.6   # Higher = stricter relevance filter
```

---

### 💬 Feature 2: Context-Aware Multi-Turn Chat

Multi-turn chat keeps a conversation history per session and scopes retrieval to specific documents.

**Step 1 — Create a chat session via the backend**

The backend creates sessions in the `rag.chat_sessions` table and returns a `session_id` UUID.

**Step 2 — Send a message**

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session-UUID>",
    "message": "Explain Newton'\''s second law",
    "allowed_document_ids": ["<doc-UUID-1>", "<doc-UUID-2>"],
    "user_id": "<user-UUID>"
  }'
```

The service:
1. Loads the last 10 messages from `rag.chat_messages` for context
2. Classifies whether the question depends on prior conversation
3. Rewrites the query if needed (e.g. "what about the second one?" → full resolved question)
4. Runs the full hybrid retrieval + rerank + LLM pipeline
5. Returns `{ answer, citations }`

**Step 3 — Continue the conversation**

Just keep sending messages with the same `session_id`. History is persisted automatically.

---

### 🗺️ Feature 3: Knowledge Graph

The Knowledge Graph extracts entities and typed relationships from documents and stores them in Neo4j for structured multi-hop reasoning.

**Prerequisites:**
- Neo4j running (see [Installation](#installation) for Docker command)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` set in `.env`

**Step 1 — Verify Neo4j connection**

```bash
# Check that Neo4j is reachable
curl http://localhost:7474/

# Or open the browser UI
open http://localhost:7474
# Default credentials: neo4j / your_password
```

**Step 2 — Ensure the document exists in PostgreSQL first**

The KG builder validates that `document_id` and `subject_id` exist in the `content.documents` and `content.subjects` tables before writing anything to Neo4j. If the document hasn't been processed through the RAG pipeline first, you'll get a `404` error.

```
document_id must exist in content.documents
subject_id  must exist in content.subjects (created by backend)
```

**Step 3 — Build the Knowledge Graph**

```bash
curl -X POST http://localhost:8000/kg/build \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "<doc-UUID>",
    "subject_id": "<subject-UUID>",
    "user_id": "<user-UUID>",
    "subject_name": "Machine Learning",
    "filename": "ml_lecture3.pdf"
  }'
```

The service will:
1. Load chunks from PostgreSQL for this document
2. Run the LLM extraction prompt on each chunk — it auto-detects the domain (`programming_cs`, `medical_healthcare`, `physics_science`, `mathematics`, `business_economics`, `history_social`, `other`)
3. Extract typed entities and domain-specific relationships (e.g. `INHERITS_FROM`, `TREATS`, `DEFINED_BY`)
4. Persist everything to Neo4j with structural nodes: `(User) → (Subject) → (Document) → (Entity)`
5. Build cross-document relationships linking shared entities across files in the same subject

**Step 4 — Query the graph**

```bash
# Get full document subgraph
curl http://localhost:8000/kg/document/<doc-UUID>

# Ask a KG-powered question
curl -X POST http://localhost:8000/kg/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What algorithms use gradient descent?",
    "subject_id": "<subject-UUID>",
    "user_id": "<user-UUID>"
  }'
```

**Step 5 — Clean up**

```bash
# Remove a single document from the graph
curl -X DELETE http://localhost:8000/kg/document/<doc-UUID>

# Remove an entire subject's graph
curl -X DELETE http://localhost:8000/kg/subject/<subject-UUID>
```

**Inspect the graph in the Neo4j browser:**

Open `http://localhost:7474` and run:
```cypher
// See all entities for a document
MATCH (e:Entity {document_id: "<doc-UUID>"}) RETURN e LIMIT 50

// See relationships between entities
MATCH (a:Entity)-[r]->(b:Entity) RETURN a, r, b LIMIT 100
```

> **Note:** The KG is non-fatal at startup. If Neo4j is unreachable when the service starts, the app continues to run — only KG endpoints will return errors.

---

### 🎙️ Feature 4: Voice Interface (STT + TTS)

The voice interface lets students speak questions and hear answers. All processing is **fully offline** using locally bundled ONNX models.

**Models included in the repo:**
- `audio/models/en_US-amy-medium.onnx` — English TTS (Piper)
- `audio/models/ar_JO-kareem-medium.onnx` — Arabic TTS (Piper)
- Faster-Whisper `medium` model (downloaded automatically on first run)

**Step 1 — Install audio system dependencies**

```bash
# Ubuntu / Debian
sudo apt-get install -y ffmpeg libsndfile1 portaudio19-dev

# macOS
brew install ffmpeg libsndfile portaudio
```

**Step 2 — Configure Whisper device** (optional, defaults to CPU)

```env
# .env
WHISPER_DEVICE=cpu          # safe default, works everywhere
WHISPER_COMPUTE_TYPE=int8   # efficient CPU inference

# For GPU (requires CUDA 12 + cuDNN):
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

**Step 3 — Test Speech-to-Text**

```bash
curl -X POST http://localhost:8000/audio/stt \
  -F "audio=@/path/to/question.wav"
```

Response:
```json
{ "transcript": "What is backpropagation?", "confidence": 0.94 }
```

**Step 4 — Test Text-to-Speech**

```bash
curl -X POST http://localhost:8000/audio/tts \
  -H "Content-Type: application/json" \
  -d '{ "text": "Backpropagation is an algorithm used to train neural networks." }' \
  --output answer.wav
```

The language is auto-detected: Arabic text → Coqui TTS (ar_JO-kareem), English → Piper TTS (en_US-amy).

**Step 5 — Full voice chat round-trip**

```bash
curl -X POST http://localhost:8000/voice/ask-audio \
  -F "audio=@question.wav" \
  -F "session_id=<session-UUID>" \
  -F "user_id=<user-UUID>" \
  -F 'allowed_document_ids=["<doc-UUID>"]'
```

Response: a WAV audio file URL pointing to `static/audio/<uuid>.wav`

> **Important:** The `static/audio/` directory must exist before starting the service. Run `mkdir -p static/audio` from inside `ai_service/`.

---

### 🌐 Feature 5: Web Search (via n8n)

When uploaded documents don't cover a topic, the AI service can fall back to a live web search orchestrated by an n8n workflow.

**How it works:**
```
Student question → AI service → POST to n8n webhook → n8n searches the web
    → n8n LLM synthesizes answer → AI service cleans + returns answer + sources
```

**Step 1 — Install and start n8n**

```bash
# Option A: npm (global)
npm install -g n8n
n8n start

# Option B: Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# n8n UI available at: http://localhost:5678
```

**Step 2 — Import the web search workflow**

The workflow definition is in the `web-search-(n8n)` branch of this repository.

```bash
# Clone the n8n branch
git clone --branch "web-search-(n8n)" https://github.com/Rehab-Hamdy/Agentic-AI-Tutor.git n8n-workflow
```

Then in the n8n UI:
1. Go to **Workflows** → **Import from file**
2. Import the workflow JSON from the cloned branch
3. Activate the workflow

**Step 3 — Configure the webhook URL**

By default the AI service expects n8n at `http://localhost:5678/webhook/web-search`. Set this in your `.env`:

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/web-search
```

If n8n is on a different host or the workflow uses a different path, update this value.

**Step 4 — Test the web search endpoint**

```bash
curl -X POST http://localhost:8000/web-search \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session-UUID>",
    "question": "What is the latest version of PyTorch?"
  }'
```

Response:
```json
{
  "answer": "PyTorch 2.x is the latest stable release...",
  "sources": [
    { "title": "PyTorch Official", "url": "https://pytorch.org", "domain": "pytorch.org" }
  ]
}
```

**Step 5 — Verify n8n is connected**

If n8n is not running, the endpoint gracefully returns:
```json
{
  "answer": "Web search is unavailable. The n8n workflow could not be reached...",
  "sources": []
}
```
This means your n8n instance isn't running or the webhook URL is wrong — the rest of the AI service continues working normally.

---

### 🎯 Feature 6: MCQ Quiz Generation

The quiz pipeline processes documents through a Bloom-taxonomy classifier and generates high-quality multiple-choice questions using the LLM.

**How the pipeline works:**

```
Document → extract text → quiz_cleaner → quiz_chunker
    → quiz_metadata (LLM: assign bloom_level + concepts + keywords)
    → quiz_chunks saved to PostgreSQL
    → quiz_prompt_builder (build per-slot prompts)
    → quiz_slot_selector (diversity-aware slot selection)
    → quiz_generator (LLM MCQ inference)
    → MCQs returned to backend → saved to DB
```

**Step 1 — Process a document for quiz generation**

```bash
curl -X POST http://localhost:8000/quiz/process \
  -F "file=@/path/to/lecture.pdf" \
  -F "document_id=<doc-UUID>"
```

This returns a list of Bloom-tagged chunks:
```json
[
  {
    "chunk_id": "uuid",
    "chunk_text": "Gradient descent is an optimization algorithm...",
    "bloom_level": "understand",
    "chunk_type": "definition",
    "concepts": ["gradient descent", "optimization"],
    "keywords": ["learning rate", "convergence"],
    "context_prev_sentence": "...",
    "context_next_sentence": "..."
  }
]
```

**Bloom levels assigned:** `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create`

**Step 2 — Generate MCQs**

```bash
curl -X POST http://localhost:8000/quiz/generate \
  -H "Content-Type: application/json" \
  -d '{
    "chunks": [ ... ],       
    "number_of_questions": 10,
    "mcqs_per_chunk": 4
  }'
```

- `number_of_questions`: how many MCQs the student will receive (1–50)
- `mcqs_per_chunk`: how many slot candidates to generate per chunk (1–4, default 4). More = larger pool for the diversity selector

Response:
```json
{
  "mcqs": [
    {
      "question_text": "Which of the following best describes gradient descent?",
      "options": [
        { "label": "A", "text": "An algorithm that randomly selects weights" },
        { "label": "B", "text": "An optimization algorithm that minimizes a loss function" },
        { "label": "C", "text": "A regularization technique" },
        { "label": "D", "text": "A type of activation function" }
      ],
      "correct_option": "B",
      "explanation": "Gradient descent iteratively updates parameters in the direction that reduces the loss...",
      "concept": "gradient descent",
      "bloom_level": "understand",
      "chunk_id": "uuid"
    }
  ],
  "requested_count": 10,
  "available_slots": 24,
  "generated_count": 10
}
```

**Step 3 — Inspect generation trace logs**

Every `/quiz/generate` call writes a detailed JSON trace log to `ai_service/logs/`:

```bash
ls ai_service/logs/
# quiz_trace_20240610_143022.json

cat ai_service/logs/quiz_trace_20240610_143022.json
# Contains: slot generation, slot selection (bloom distribution, chunk distribution),
# inference results, elapsed time
```

**Tuning MCQ quality:**

Edit `ai_service/app/quiz/quiz_config.py`:

```python
# Minimum words per chunk (below this → chunk dropped)
min_words: int = 35

# Quality gate — composite score (0–1, below this → chunk dropped)
quality_score_threshold: float = 0.50

# Bloom taxonomy model rotation order (on rate-limit, tries next)
models: tuple = (
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
)
```

---

### 📊 Feature 7: Evaluation Suite

The evaluation scripts benchmark retrieval and generation quality against standard datasets.

**Step 1 — Install additional evaluation dependencies**

```bash
pip install ragas datasets openai cohere langchain langchain-openai
```

**Step 2 — Run RAGAS evaluation**

RAGAS measures: faithfulness, answer relevancy, context precision, context recall.

```bash
# Set your OpenAI or Cohere key for RAGAS judge
export OPENAI_API_KEY=your_key

python -m app.evaluation.ragas_eval
```

**Step 3 — Run NQ (Natural Questions) benchmark**

```bash
# Download NQ dataset first
python -m app.evaluation.nq_download

# Run retrieval evaluation
python -m app.evaluation.eval_nq
```

**Step 4 — Run HotpotQA multi-hop benchmark**

```bash
python -m app.evaluation.hotpot_download
python -m app.evaluation.eval_hotpot
```

---

## Evaluation Suite

The `evaluation/` directory contains scripts to benchmark retrieval quality:

```bash
# RAGAS evaluation (requires OpenAI API key or Cohere)
python -m app.evaluation.ragas_eval

# Natural Questions benchmark
python -m app.evaluation.eval_nq

# HotpotQA multi-hop benchmark
python -m app.evaluation.eval_hotpot
```

---

## Project Structure

```
ai_service/
├── .env                          # Environment variables (not committed)
├── requirements.txt              # Python dependencies
├── app/
│   ├── main.py                   # FastAPI app entry point
│   ├── db.py                     # Database connection
│   ├── llm.py                    # LLM client with retry/fallback
│   ├── embedding.py              # Sentence-transformer embeddings
│   ├── extract.py                # Multi-format file parser
│   ├── parsers.py                # Per-format parsing helpers
│   ├── text_cleaner.py           # Text normalization
│   ├── chunker.py                # Adaptive semantic chunker
│   ├── vector_store.py           # pgvector search
│   ├── search.py                 # Hybrid BM25 + dense retrieval
│   ├── reranker.py               # Cross-encoder reranker
│   ├── rag.py / rag_service.py   # RAG Q&A pipeline
│   ├── chat.py / chat_service.py # Multi-turn chat
│   ├── voice.py                  # Voice chat endpoint
│   ├── vstt.py / vtts.py         # STT / TTS route files
│   ├── web_search_chat.py        # Web search chat
│   ├── web_search_service.py     # n8n webhook client
│   ├── kg.py                     # KG API routes
│   ├── kg_extractor.py           # LLM entity/relation extraction
│   ├── kg_service.py             # KG build + retrieval logic
│   ├── kg_db.py / kg_store.py    # Neo4j CRUD
│   ├── kg_pipeline.py            # KG ingestion orchestrator
│   ├── audio/
│   │   ├── tts.py                # Piper TTS
│   │   ├── stt.py                # Faster-Whisper STT
│   │   ├── hybrid_tts.py         # Multi-backend TTS
│   │   └── models/               # Piper ONNX model files
│   ├── quiz/
│   │   ├── quiz_router.py        # /quiz/process endpoint
│   │   ├── quiz_generate_router.py # /quiz/generate endpoint
│   │   ├── quiz_prompt_builder.py  # LLM prompt construction
│   │   ├── quiz_slot_selector.py   # Diversity-aware selection
│   │   ├── quiz_generator.py       # LLM MCQ inference
│   │   ├── quiz_cleaner.py         # Output validation
│   │   └── quiz_metadata.py        # Bloom taxonomy tagging
│   └── evaluation/
│       ├── ragas_eval.py
│       ├── eval_nq.py
│       ├── eval_hotpot.py
│       └── ...
└── static/
    └── audio/                    # Generated TTS audio files
```

---

## Notes

- **LLM fallback chain:** If the primary model hits a rate-limit or context-window error, the service automatically retries with fallback models (`llama-3.2-3b-preview`, `gemma2-9b-it`, `mixtral-8x7b-32768`).
- **Multi-language support:** Piper TTS includes both English (`en_US-amy-medium`) and Arabic (`ar_JO-kareem-medium`) ONNX models. Language is auto-detected.
- **Offline-first:** All embedding, reranking, chunking, and TTS models run locally. Only LLM generation calls an external API (Groq).
- **Knowledge Graph is optional:** The app starts successfully even if Neo4j is unavailable (`lifespan` catches the schema-init error non-fatally).
