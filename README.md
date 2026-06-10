# Agentic AI Tutor

> A personalized learning platform powered by Agentic AI and Retrieval-Augmented Generation.  
> Students upload their own course materials and get citation-backed explanations, adaptive quizzes, voice interaction, and guided study support — grounded entirely in their own documents.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![.NET](https://img.shields.io/badge/.NET-8.0-purple.svg)](https://dotnet.microsoft.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://postgresql.org)

---

## Table of Contents

- [What is Agentic AI Tutor?](#what-is-agentic-ai-tutor)
- [System Components](#system-components)
- [Repository Branches](#repository-branches)
- [High-Level Architecture](#high-level-architecture)
- [Feature Overview](#feature-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Guides](#detailed-setup-guides)
- [How It Works](#how-it-works)
- [Project Team](#project-team)

---

## What is Agentic AI Tutor?

Agentic AI Tutor is a full-stack educational platform that transforms students' own course materials into an intelligent, interactive study assistant. Unlike general-purpose chatbots, it answers questions **exclusively from uploaded documents**, providing precise citations so students always know where information came from.

**Core capabilities:**

- **RAG-powered Q&A** — Ask questions and receive answers sourced directly from your uploaded PDFs, slides, and documents, with exact page-level citations
- **Adaptive Quiz Generation** — Automatically generate Bloom-taxonomy-aligned multiple-choice questions from any uploaded material
- **Knowledge Graph** — Extract entities and relationships from documents to enable structured, multi-hop reasoning
- **Voice Interaction** — Speak questions and hear answers via offline speech-to-text and text-to-speech
- **Web Search Fallback** — When documents don't contain the answer, optionally search the web and cite live sources
- **Multi-format Support** — PDF, PPTX, DOCX, TXT, CSV, and scanned images (OCR)

---

## System Components

The platform is built as three cooperating layers across multiple repository branches:

| Component | Branch | Technology | Role |
|-----------|--------|------------|------|
| **AI Service** | `AI` | Python · FastAPI | Document intelligence, embeddings, LLM, voice |
| **Backend API** | `backend` | ASP.NET Core 8 | Auth, persistence, orchestration, quiz lifecycle |
| **Mobile Frontend** | `frontend` | Flutter | Cross-platform mobile UI |
| **Web Search Agent** | `web-search-(n8n)` | n8n | Workflow automation for live web search |
| **Quiz Fine-tuning** | `quiz-data-generation-and-finetuning` | Python · LLaMA-Factory | LoRA fine-tuning of MCQ generation model |

---

## Repository Branches

```
main                              ← Project description
├── AI                        ← Python AI service (this README + AI README)
├── backend                       ← ASP.NET Core API (backend README)
├── frontend                      ← Flutter mobile app
├── web-search-(n8n)              ← n8n web search workflow
└── quiz-data-generation-and-finetuning  ← MCQ model fine-tuning pipeline
```

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Flutter Mobile App                             │
│                         (frontend branch)                             │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  REST API (JWT Bearer)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   ASP.NET Core 8 Backend                              │
│                      (backend branch)                                 │
│                                                                       │
│  • User Auth (JWT + BCrypt)     • Document Management                 │
│  • Chat Session / Message       • Quiz Lifecycle                      │
│  • Background Jobs (Hangfire)   • Email Notifications                 │
└────────────────────────┬──────────────────────────────┬──────────────┘
                         │  HTTP                         │  SQL (EF Core)
                         ▼                               ▼
┌────────────────────────────────┐      ┌────────────────────────────┐
│    Python AI Service       │      │        PostgreSQL           │
│       (AI branch)          │      │       + pgvector            │
│                                │      │                             │
│  • Document Parsing (OCR)      │      │  Schemas:                   │
│  • Semantic Chunking           │      │  public, auth, content,     │
│  • e5-base-v2 Embeddings       │      │  rag, quiz, planner         │
│  • BM25 + Dense Retrieval      │      └────────────────────────────┘
│  • BGE Reranker                │
│  • Groq LLM (llama-3.1-8b)     │      ┌────────────────────────────┐
│  • Knowledge Graph (Neo4j)     │      │          Neo4j             │
│  • MCQ Generation              │      │    (Knowledge Graph)        │
│  • Voice: Piper + Whisper      │      └────────────────────────────┘
└────────────────────────────────┘
                │
                │  Webhook (web search)
                ▼
┌────────────────────────────────┐
│          n8n Workflow           │
│   (web-search-(n8n) branch)    │
└────────────────────────────────┘
```

---

## Feature Overview

### 📄 Document Management
Upload PDFs, PPTX, DOCX, TXT, CSV, or images. The system automatically extracts text (with OCR for scanned content), semantically chunks it, generates vector embeddings, and stores everything in PostgreSQL — ready for intelligent search.

### 💬 RAG-Powered Chat
Ask any question about your uploaded materials. The system retrieves the most relevant passages using a hybrid BM25 + dense retrieval pipeline, reranks them with a cross-encoder, then synthesizes an answer with the LLM — citing exact documents and page numbers.

### 🗺️ Knowledge Graph
For subjects where structured relationships matter, the platform builds a Neo4j knowledge graph from your documents — extracting typed entities and domain-specific relationships. The KG enables multi-hop reasoning that pure vector search can't provide.

### 🎯 Quiz Generation
Trigger MCQ generation for any document. The AI service processes chunks with Bloom taxonomy classification (remember / understand / apply / analyze / evaluate / create), then generates high-quality multiple-choice questions with explanations. Students can attempt quizzes, review answers, and track history.

### 🎙️ Voice Interface
Students can speak questions using the device microphone. Faster-Whisper transcribes audio to text, the RAG pipeline processes the question, and Piper TTS synthesizes the answer back as audio — entirely offline, supporting both English and Arabic.

### 🌐 Web Search Fallback
When uploaded documents don't cover a topic, students can enable web search mode. An n8n workflow orchestrates a live web search, and the LLM synthesizes an answer with live source citations.

---

## Tech Stack

### AI Service (Python)
| Technology | Version | Use |
|------------|---------|-----|
| FastAPI | latest | API framework |
| Sentence-Transformers | — | `intfloat/e5-base-v2` embeddings, `all-MiniLM-L6-v2` chunking |
| BAAI/bge-reranker-base | — | Cross-encoder reranking |
| Groq API | — | LLM (llama-3.1-8b-instant) with model fallback chain |
| pgvector | — | Vector similarity search in PostgreSQL |
| Neo4j | 5.x | Knowledge graph storage |
| PyMuPDF + python-pptx + python-docx | — | Multi-format document parsing |
| Tesseract OCR | 4.x | Scanned document / image text extraction |
| Faster-Whisper | — | Offline speech-to-text (medium model) |
| Piper TTS | — | Offline text-to-speech (EN + AR ONNX models) |
| rank_bm25 | — | BM25 lexical retrieval |
| torch | 2.1.2 | ML runtime |

### Backend (C# / .NET)
| Technology | Version | Use |
|------------|---------|-----|
| ASP.NET Core | 8.0 | Web API framework |
| Entity Framework Core | 8.0 | ORM |
| Npgsql + pgvector | 8.0.x | PostgreSQL provider with vector support |
| Hangfire + Hangfire.PostgreSql | 1.8.x | Background job processing |
| JWT Bearer Auth | 8.0 | Stateless authentication |
| BCrypt.Net-Next | 4.0.3 | Password hashing |
| FluentValidation | 8.6 | Input validation |
| MailKit | 4.x | Email delivery |
| Polly | — | HTTP resilience for AI service calls |
| Swashbuckle | 6.4 | OpenAPI / Swagger documentation |

### Database
| Technology | Use |
|------------|-----|
| PostgreSQL 14+ | Primary relational store + pgvector for embeddings |
| Neo4j 5.x | Knowledge graph (entities + relationships) |

---

## Prerequisites

Before starting, ensure the following are installed on your system:

| Requirement | Notes |
|-------------|-------|
| **Python 3.10+** | 3.11 recommended for the AI service |
| **.NET 8 SDK** | For the backend service |
| **PostgreSQL 14+** | With `pgvector` extension |
| **Neo4j 5.x** | For knowledge graph features (optional but recommended) |
| **Tesseract OCR 4.x** | For scanned PDF / image parsing |
| **Poppler** | Required by `pdf2image` for PDF rendering |
| **Git** | To clone the repository |

---

## Quick Start

The platform requires three services running simultaneously: the AI Python service, the ASP.NET Core backend, and a PostgreSQL database (+ optionally Neo4j).

### Step 1: Clone the repository

```bash
git clone https://github.com/Rehab-Hamdy/Agentic-AI-Tutor.git
cd Agentic-AI-Tutor
```

### Step 2: Set up PostgreSQL

```sql
CREATE DATABASE "AgenticAITutor";
\c "AgenticAITutor"
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS quiz;
CREATE SCHEMA IF NOT EXISTS planner;
```

### Step 3: Start the AI Service

```bash
git checkout AI
cd ai_service

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install system dependencies (Ubuntu)
sudo apt-get install -y tesseract-ocr poppler-utils ffmpeg libsndfile1

# Install Python packages
pip install -r requirements.txt

# Configure environment
cp .env.example .env        # Edit with your credentials
mkdir -p static/audio

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Service available at: `http://localhost:8000` · Docs at: `http://localhost:8000/docs`

### Step 4: Start the Backend API

```bash
# Open a new terminal
cd Agentic-AI-Tutor
git checkout backend
cd Backend/AgenticAITutor/AgenticAITutor

# Configure appsettings.json
# Set ConnectionStrings.DefaultConnection to your PostgreSQL URL
# Set AIService.BaseURL to http://localhost:8000

# Restore packages and apply migrations
dotnet restore
dotnet ef database update

# Start the backend
dotnet run
```

API available at: `http://localhost:5000` · Swagger at: `http://localhost:5000/swagger`

### Step 5: Connect the Flutter App

```bash
# Open a new terminal
cd Agentic-AI-Tutor
git checkout frontend
cd flutter_app         # adjust to actual directory name

flutter pub get
flutter run
```

---

## Detailed Setup Guides

For in-depth installation instructions, environment variable references, and module documentation for each service, see the dedicated README files:

- **[AI Service README](https://github.com/Rehab-Hamdy/Agentic-AI-Tutor/blob/AI/README.md)** — Python AI service setup, all endpoints, architecture diagrams, evaluation suite
- **[Backend README](https://github.com/Rehab-Hamdy/Agentic-AI-Tutor/blob/backend/README.md)** — ASP.NET Core setup, all API controllers, database schema, Hangfire jobs

---

## End-to-End Feature Setup

This section walks through setting up and verifying every feature of the platform from scratch, in the correct order. Each feature builds on the previous one.

---

### ✅ Step 0: Start All Services

Before using any feature, all three services must be running:

```bash
# Terminal 1 — PostgreSQL (if not running as a system service)
pg_ctl start -D /usr/local/var/postgresql@14

# Terminal 2 — Neo4j (for Knowledge Graph)
docker run --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword neo4j:5

# Terminal 3 — AI Python service
cd Agentic-AI-Tutor && git checkout AI && cd ai_service
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 4 — ASP.NET Core Backend
cd Agentic-AI-Tutor && git checkout backend
cd Backend/AgenticAITutor/AgenticAITutor
dotnet run

# Terminal 5 — n8n (for Web Search feature only)
n8n start
```

**Verify everything is up:**

| Service | URL | Expected |
|---------|-----|----------|
| AI Docs | `http://localhost:8000/docs` | Swagger UI |
| Backend Swagger | `http://localhost:5000/swagger` | Swagger UI |
| Neo4j Browser | `http://localhost:7474` | Graph UI |
| Hangfire Dashboard | `http://localhost:5000/hangfire` | Job queue |
| n8n UI | `http://localhost:5678` | Workflow editor |

---

### 📁 Feature 1: Upload a Document and Enable RAG

This is the foundation. Every other feature (chat, KG, quiz) depends on uploaded documents.

**1. Register and log in** via the backend API (or the Flutter app):

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{ "fullName": "Test User", "email": "test@example.com", "password": "Pass123!" }'

# Login → save the token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{ "email": "test@example.com", "password": "Pass123!" }' | jq -r '.token')
```

**2. Create a subject:**

```bash
SUBJECT_ID=$(curl -s -X POST http://localhost:5000/api/subject \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "name": "Machine Learning" }' | jq -r '.id')
```

**3. Upload a document:**

```bash
DOC_ID=$(curl -s -X POST http://localhost:5000/api/document \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/lecture.pdf" \
  -F "subjectId=$SUBJECT_ID" \
  -F "title=Lecture 1" | jq -r '.id')
```

**4. Wait for processing:** The Hangfire job calls the AI service to embed the document. Poll the status:

```bash
watch -n 3 "curl -s http://localhost:5000/api/document \
  -H 'Authorization: Bearer $TOKEN' | jq '.[] | {title, processingStatus}'"
```

When `processingStatus = "Completed"`, the document is ready for RAG.

---

### 💬 Feature 2: RAG Chat

**1. Create a chat session:**

```bash
SESSION_ID=$(curl -s -X POST http://localhost:5000/api/chat-session \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Study Session\", \"subjectId\": \"$SUBJECT_ID\"}" | jq -r '.id')
```

**2. Ask a question:**

```bash
curl -X POST http://localhost:5000/api/chat-message/text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"sessionId\": \"$SESSION_ID\",
    \"content\": \"What is backpropagation?\",
    \"documentIds\": [\"$DOC_ID\"]
  }"
```

The response includes an `answer` and `citations` with `documentId`, `pageStart`, `pageEnd`.

**3. Ask follow-up questions** with the same `sessionId` — the service uses conversation history to resolve pronouns and context references automatically.

---

### 🗺️ Feature 3: Knowledge Graph

Requires the document to be fully embedded (Feature 1 complete).

**1. Trigger KG construction:**

```bash
curl -X POST http://localhost:5000/api/chunk/kg \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"documentId\": \"$DOC_ID\", \"subjectId\": \"$SUBJECT_ID\"}"
```

The AI service's LLM extracts entities and domain-typed relationships, then persists them to Neo4j.

**2. Verify in Neo4j Browser** (`http://localhost:7474`):

```cypher
MATCH (e:Entity)-[r]->(e2:Entity)
RETURN e.name, type(r), e2.name
LIMIT 50
```

**3. Ask KG-powered questions** — the AI service uses the graph for multi-hop reasoning alongside vector retrieval, giving richer answers about relationships between concepts.

**4. Clean up** when deleting documents — the backend automatically removes KG nodes:
```bash
curl -X DELETE http://localhost:5000/api/document/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"
# This also calls the AI service to remove Neo4j nodes for this document
```

---

### 🎯 Feature 4: Quiz Generation

**1. Initiate a quiz:**

```bash
QUIZ_ID=$(curl -s -X POST http://localhost:5000/api/quiz/initiate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"documentId\": \"$DOC_ID\",
    \"numberOfQuestions\": 10,
    \"mcqsPerChunk\": 4
  }" | jq -r '.quizId')
```

**2. Poll for readiness** (generation usually takes 30–120 seconds depending on document size):

```bash
watch -n 5 "curl -s http://localhost:5000/api/quiz/$QUIZ_ID/status \
  -H 'Authorization: Bearer $TOKEN' | jq '.status'"
```

**3. Start the quiz:**

```bash
curl http://localhost:5000/api/quiz/$QUIZ_ID/start \
  -H "Authorization: Bearer $TOKEN"
```

**4. Submit answers:**

```bash
curl -X POST http://localhost:5000/api/quiz/$QUIZ_ID/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      { "questionId": "<q1-UUID>", "selectedOption": "B" },
      { "questionId": "<q2-UUID>", "selectedOption": "C" }
    ]
  }'
```

**5. Review with explanations:**

```bash
curl http://localhost:5000/api/quiz/$QUIZ_ID/review \
  -H "Authorization: Bearer $TOKEN"
```

---

### 🎙️ Feature 5: Voice Interface

The voice interface works fully offline. No API keys needed beyond what's already configured.

**1. Install system audio dependencies:**

```bash
# Ubuntu
sudo apt-get install -y ffmpeg libsndfile1

# macOS
brew install ffmpeg libsndfile
```

**2. Test STT directly:**

```bash
curl -X POST http://localhost:8000/audio/stt \
  -F "audio=@/path/to/question.wav"
# → { "transcript": "What is a neural network?", "confidence": 0.95 }
```

**3. Test TTS directly:**

```bash
curl -X POST http://localhost:8000/audio/tts \
  -H "Content-Type: application/json" \
  -d '{ "text": "A neural network is a computational model." }' \
  --output answer.wav
```

**4. Full voice chat round-trip (via backend):**

```bash
curl -X POST http://localhost:5000/api/chat-message/voice \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@question.wav" \
  -F "sessionId=$SESSION_ID" \
  -F "documentIds=[\"$DOC_ID\"]"
```

The backend proxies to the AI service: audio → STT → RAG → TTS → returns both text answer and audio URL.

> **Arabic support:** The TTS engine auto-detects language. Arabic text triggers the Coqui TTS engine with the `ar_JO-kareem-medium` model. English uses Piper's `en_US-amy-medium`.

---

### 🌐 Feature 6: Web Search

Requires n8n running with the web search workflow imported and activated.

**1. Start n8n and import the workflow:**

```bash
# Start n8n
docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n

# Clone the workflow definition
git clone --branch "web-search-(n8n)" https://github.com/Rehab-Hamdy/Agentic-AI-Tutor.git n8n-workflow
```

In the n8n UI (`http://localhost:5678`):
1. **Import** the workflow JSON from the cloned directory
2. **Activate** the workflow (toggle in the top-right)
3. Confirm the webhook path is `/webhook/web-search`

**2. Set the webhook URL in the AI service `.env`:**

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/web-search
```

Restart the AI service after changing `.env`.

**3. Send a web search message via backend:**

```bash
curl -X POST http://localhost:5000/api/chat-message/web-search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"sessionId\": \"$SESSION_ID\",
    \"content\": \"What are the best practices for fine-tuning LLMs in 2025?\"
  }"
```

Response includes `answer` text and `sources` array with URLs and domain names.

**If n8n is not running**, the endpoint returns a graceful error message — it does not crash the rest of the platform.

---

## How It Works

### Document Upload Flow

```
Student uploads file (PDF / PPTX / DOCX / image)
    │
    ▼
Backend saves file metadata to PostgreSQL
    │
    ▼
Hangfire queues DocumentChunkingJob (async)
    │
    ▼
Backend → POST ai_service/extract/embed
    │
    ▼
AI Service: parse → clean → chunk → embed (e5-base-v2) → store in pgvector
    │
    ▼
Document status: Pending → Processing → Completed
```

### Chat / Q&A Flow

```
Student sends question (text or voice)
    │
    ├─ voice → STT (Faster-Whisper) → transcribed text
    │
    ▼
Backend → POST ai_service/chat/  (with session_id + document scope)
    │
    ▼
AI Service:
  1. Embed question (e5-base-v2, "query: ..." prefix)
  2. Hybrid retrieval: dense (pgvector cosine) + BM25
  3. Cross-encoder reranking (BAAI/bge-reranker-base)
  4. Build context with citations
  5. LLM generation (Groq llama-3.1-8b-instant)
    │
    ▼
Backend stores message + citations → returns to Flutter app
    │
    └─ tts requested → TTS (Piper) → audio file URL
```

### Quiz Generation Flow

```
Student requests quiz for a document
    │
    ▼
Backend creates Quiz record (status: Generating)
    │
    ▼
Hangfire queues QuizGenerationJob
    │
    ▼
Backend → POST ai_service/quiz/process  (extract Bloom-tagged chunks)
    │
    ▼
Backend saves quiz_chunks to PostgreSQL
    │
    ▼
Backend → POST ai_service/quiz/generate  (LLM MCQ generation)
    │
    ▼
MCQs saved: quiz_questions + quiz_options tables
    │
    ▼
Quiz status: Generating → Ready
    │
    ▼
Student starts quiz → submits answers → gets score + review
```

---

## Project Team

This platform was developed as a graduation project by a multidisciplinary six-person team.

| Team Member | Responsibility |
|-------------|---------------|
| Rehab Hamdy | AI Engineer |
| Aya Khaled | AI Engineer |
| Aya Mohamed | AI Engineer |
| Shahd Elsayed | AI Engineer |
| Ahmed Maghawry | Full Stack Developer |
| Abdelrahman Mohamed | Mobile Frontend Developer |

The project was developed through parallel workstreams covering Retrieval-Augmented Generation (RAG), educational question generation, machine learning, backend services, and mobile application development.

---

*Built with ❤️ as a graduation project at Helwan University — Faculty of Computers and Artificial Intelligence (2025–2026).*
