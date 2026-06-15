<div align="center">

# 🎓 GenT — AI Tutor Assistant

### *A Hybrid Knowledge Graph and Retrieval-Augmented Generation Educational Platform with Bloom's Taxonomy-Aligned Quiz Generation*

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ASP.NET Core](https://img.shields.io/badge/ASP.NET_Core-Web_API-512BD4?style=flat-square&logo=dotnet&logoColor=white)](https://dotnet.microsoft.com)
[![React](https://img.shields.io/badge/React-Web-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph_DB-008CC1?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com)
[![License](https://img.shields.io/badge/License-Academic-green?style=flat-square)](#acknowledgements)

**Graduation Project · Capital University (formerly Helwan University) · Faculty of Computers & Artificial Intelligence · June 2026**

</div>

---

## Table of Contents

- [Project Overview](#-project-overview)
  - [Key Innovations](#key-innovations)
- [Main Features](#-main-features)
  - [Part A — AI Tutor (KG-RAG)](#part-a--ai-tutor-kg-rag)
  - [Part B — Quiz Generation](#part-b--quiz-generation)
- [Screenshots](#-screenshots)
  - [Screenshot Guide](#screenshot-guide)
- [System Architecture](#-system-architecture)
  - [High-Level Architecture](#high-level-architecture)
  - [AI Pipeline — Part A: RAG Tutor](#ai-pipeline--part-a-rag-tutor)
  - [AI Pipeline — Part B: Quiz Generation](#ai-pipeline--part-b-quiz-generation)
  - [Knowledge Graph Pipeline](#knowledge-graph-pipeline)
- [Repository Structure](#-repository-structure)
- [🛠 Technology Stack](#-technology-stack)
  - [Frontend](#frontend)
  - [Backend](#backend)
  - [AI / ML](#ai--ml)
  - [Databases](#databases)
  - [Evaluation & Benchmarking](#evaluation--benchmarking)
- [AI Components](#-ai-components)
  - [RAG System (Part A)](#rag-system-part-a)
  - [Hybrid Retrieval](#hybrid-retrieval)
  - [Knowledge Graph](#knowledge-graph)
  - [Knowledge Distillation Pipeline (Part B)](#knowledge-distillation-pipeline-part-b)
  - [LLM-as-a-Judge (CMQS)](#llm-as-a-judge-cmqs)
  - [Voice Interaction](#voice-interaction)
- [Evaluation Results](#-evaluation-results)
  - [Part A — Hybrid KG-RAG Retrieval](#part-a--hybrid-kg-rag-retrieval)
  - [Part A — End-to-End Generation Quality](#part-a--end-to-end-generation-quality)
  - [Part B — Knowledge Distillation Results](#part-b--knowledge-distillation-results)
  - [Part B — Validation Pipeline Performance](#part-b--validation-pipeline-performance)
- [🔌 API Overview](#-api-overview)
  - [ASP.NET Core Backend (selected endpoints)](#aspnet-core-backend-selected-endpoints)
  - [Python FastAPI AI Service (selected endpoints)](#python-fastapi-ai-service-selected-endpoints)
- [Installation](#-installation)
  - [Prerequisites](#prerequisites)
  - [1. AI Service (Python / FastAPI)](#1-ai-service-python--fastapi)
  - [2. Backend (ASP.NET Core)](#2-backend-aspnet-core)
  - [3. React Web App](#3-react-web-app)
- [Running the Full System Locally](#%EF%B8%8F-running-the-full-system-locally)
- [Future Improvements](#-future-improvements)
- [Team](#-team)
- [Acknowledgements](#-acknowledgements)

---

## 📋 Project Overview

Modern educational technology faces two fundamental, unsolved problems: students interacting with general-purpose LLMs receive answers that are factually hallucinated and impossible to trace back to authoritative course materials; meanwhile, educators lack scalable tools to generate pedagogically valid assessments that span the full cognitive range of Bloom's Taxonomy.

**GenT** addresses both problems within a single, unified platform through two cooperating AI subsystems:

**Part A — Hybrid KG-RAG Educational Assistant** delivers evidence-grounded, citation-backed answers over student-uploaded course materials, fusing dense vector retrieval, BM25 lexical search, cross-encoder reranking, and Neo4j knowledge graph traversal before invoking a large language model for generation. Every answer includes source attribution, a composite confidence score, and links to prerequisite concepts extracted from the document graph.

**Part B — Quiz Generation Subsystem** implements a teacher–student knowledge-distillation pipeline in which Google Gemini 2.5 Flash Lite generates a curated MCQ corpus that is validated through a five-stage pipeline and used to fine-tune Qwen2.5-1.5B-Instruct with LoRA. The result is a compact, locally deployable student model that generates Bloom's Taxonomy-aligned multiple-choice questions from the same uploaded materials — eliminating per-request cloud API costs at runtime.

### Key Innovations

- **Hybrid KG-RAG retrieval**: Reciprocal Rank Fusion (RRF) over dense + sparse retrieval channels, followed by BGE cross-encoder reranking and hop-bounded Neo4j graph traversal — all in a single, unified pipeline.
- **Distilled quiz generation**: A 1.5B student model fine-tuned on teacher-validated data, achieving near-teacher quality at a fraction of the inference cost.
- **Multi-stage MCQ validation**: Five sequential quality gates (format, relevance, distractor plausibility, deduplication, LLM-as-a-Judge holistic scoring) before any question enters storage.
- **Unified architecture**: Tutoring and assessment generation share the same ingestion foundation, isolated per-user data partitioning, and modular service layer.

---

## ✨ Main Features

### Part A — AI Tutor (KG-RAG)

| Feature | Description |
|---|---|
| **Multi-format Document Upload** | PDF, DOCX, PPTX, TXT, CSV with Tesseract OCR fallback for scanned pages and embedded images |
| **Semantic Chunking** | Adaptive sentence-embedding boundary detection (threshold = mean(sim) − 0.5 · std(sim)) preserving topical coherence |
| **Dense Vector Retrieval** | `intfloat/e5-base-v2` (768-dim) embeddings indexed in PostgreSQL with HNSW cosine index via pgvector |
| **BM25 Lexical Retrieval** | PostgreSQL Full-Text Search with tsvector indexing for sparse keyword retrieval |
| **Hybrid Fusion** | Reciprocal Rank Fusion (k=60) merging dense and sparse rankings into a unified candidate pool |
| **Cross-Encoder Reranking** | `BAAI/bge-reranker-base` neural reranking over the fused candidate pool |
| **Knowledge Graph Construction** | Entity and relationship extraction via `Llama-3.1-8B-Instant` on Groq, persisted in Neo4j with cross-document concept linking |
| **Multi-Hop Graph Retrieval** | Hop-bounded subgraph traversal (default: 2 hops) with multi-level seed matching (exact, substring, degree-based) |
| **Answer Generation** | `Llama-3.3-70B-Versatile` on Groq with hallucination-prevention prompting and citation assembly |
| **Citation Attribution** | Every answer carries source document, chunk index, and page reference |
| **Confidence Scoring** | Composite score: Confidence = w₁·R + w₂·K + w₃·G + w₄·E |
| **Voice Interaction (STT/TTS)** | OpenAI Whisper for speech-to-text; optional text-to-speech response delivery |
| **Web Search Augmentation** | Optional external search integration when local evidence is insufficient |
| **Multilingual Support** | Responses generated in the user's detected language |
| **Conversational Context** | Multi-turn session management with pronoun resolution and dependent-query rewriting |
| **Prerequisite Reasoning** | Concept dependency chains surfaced from the knowledge graph for adaptive tutoring guidance |
| **Authentication & Isolation** | JWT-secured endpoints; per-user, per-subject data partitioning at relational and graph layers |

### Part B — Quiz Generation

| Feature | Description |
|---|---|
| **Bloom's Taxonomy Alignment** | Each chunk classified against Bloom's cognitive levels; MCQs generated to match the classified level |
| **Teacher–Student Distillation** | Gemini 2.5 Flash Lite generates supervised training data; Qwen2.5-1.5B-Instruct is fine-tuned with QLoRA |
| **Five-Stage MCQ Validation** | Format → Relevance → Distractor Quality → Deduplication → LLM-as-a-Judge holistic scoring |
| **LLM-as-a-Judge Scoring** | Composite MCQ Quality Score (CMQS): 0.30·correctness + 0.20·clarity + 0.15·distractors + 0.15·educational_value + 0.20·chunk_grounding |
| **Metadata Extraction** | Per-chunk topic, key concepts, Bloom level, difficulty, and chunk type classification |
| **Slot-Based MCQ Prompting** | Structured prompting strategy producing stem, four options, correct answer, distractors, and full metadata |
| **Hugging Face Deployment** | Fine-tuned LoRA adapter published to Hugging Face Hub for reproducible inference |

---

## 📸 Screenshots

Follow a student's journey through **GenT** — from first login to mastering a topic.

### 1. Welcome aboard — the student signs in


![Login](screenshots/login.png)

---

### 2. Landing on the Dashboard


![Dashboard](screenshots/dashboard.png)

---

### 3. Organizing knowledge — Subjects & documents


![Subjects](screenshots/subjects.png)

---

### 4. Asking the AI Tutor a real question


![Chat Interface](screenshots/chat.png)

---

### 5. Seeing the answer's reasoning — the Knowledge Graph


![Knowledge Graph](screenshots/knowledge_graph.png)

---

### 6. Time to practice — generating a quiz


![Quiz Generation](screenshots/quiz_generation.png)

---

### 7. Taking the quiz


![Quiz Taking](screenshots/quiz_taking.png)

---

### 8. Learning from every answer — the review


![Quiz Review](screenshots/quiz_review.png)

---

### 9. Tracking the journey — Progress & Analytics


![Analytics Dashboard](screenshots/analytics.png)
---

## 🏗 System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph Presentation["Presentation Layer"]
        WB[React Web App]
    end

    subgraph Application["Application Layer — ASP.NET Core Web API"]
        AUTH[JWT Authentication]
        BK[Backend Controllers]
        BG[Background Processing Services]
    end

    subgraph AI["AI Service Layer — Python / FastAPI"]
        RAG[RAG Service<br/>chunk.py · kg_service.py · rag_service.py]
        QUIZ[Quiz Generation Service<br/>quiz_gen.py · validation.py]
    end

    subgraph Storage["Data Layer"]
        PG[(PostgreSQL + pgvector<br/>Chunks · Embeddings · Sessions)]
        NEO[(Neo4j<br/>Knowledge Graph)]
        SQL[(PostgreSQL Relational<br/>Users · Subjects · Quizzes)]
    end

    subgraph External["External APIs"]
        GROQ[Groq API<br/>Llama-3.1-8B · Llama-3.3-70B]
        GEM[Google Gemini<br/>2.5 Flash Lite — offline only]
        WHISPER[OpenAI Whisper<br/>STT]
        SEARCH[Web Search API]
    end

    WB --> AUTH
    AUTH --> BK
    BK --> BG
    BK --> RAG
    BK --> QUIZ
    RAG --> PG
    RAG --> NEO
    RAG --> GROQ
    RAG --> WHISPER
    RAG --> SEARCH
    QUIZ --> GROQ
    QUIZ --> GEM
    BG --> PG
    BG --> SQL
```

### AI Pipeline — Part A: RAG Tutor

```mermaid
flowchart LR
    subgraph Offline["Offline — Ingestion Phase"]
        A[Document Upload<br/>PDF · DOCX · PPTX · TXT · CSV] --> B[Format Parsing<br/>+ Tesseract OCR]
        B --> C[Multi-Stage Text Cleaning<br/>Unicode · Ligatures · OCR Artefacts]
        C --> D[Semantic Chunking<br/>Sentence-Embedding Boundary Detection]
        D --> E[Metadata Extraction<br/>Source · Pages · Entities · Tags]
        E --> F[E5 Embedding<br/>768-dim dense vectors]
        F --> G[(pgvector<br/>HNSW Index)]
        E --> H[Entity & Relation Extraction<br/>Llama-3.1-8B-Instant · Groq]
        H --> I[(Neo4j<br/>Knowledge Graph)]
    end

    subgraph Online["Online — Inference Phase"]
        J[User Query<br/>Text or Voice] --> K[Query Understanding<br/>Context Resolution · Rewriting]
        K --> L[Dense Retrieval<br/>pgvector cosine]
        K --> M[Sparse Retrieval<br/>BM25 / Full-Text Search]
        K --> N[KG Traversal<br/>Entity NER · Hop-Bounded]
        L --> O[RRF Fusion k=60]
        M --> O
        O --> P[BGE Cross-Encoder<br/>Reranking]
        N --> Q[Subgraph Context]
        P --> R[Context Assembly<br/>Chunks + Graph Relations]
        Q --> R
        R --> S[Llama-3.3-70B-Versatile<br/>Answer Generation · Groq]
        S --> T[Response with Citations<br/>+ Confidence Score]
    end

    G --> L
    I --> N
```

### AI Pipeline — Part B: Quiz Generation

```mermaid
flowchart TB
    subgraph Training["Offline — Distillation & Fine-Tuning"]
        S1[S1: Document Processing<br/>PDF · DOCX · PPTX · OCR] --> S2[S2: Semantic Chunking<br/>Adaptive Boundary Detection]
        S2 --> S3[S3: Metadata Extraction<br/>Topic · Bloom Level · Concepts]
        S3 --> S4[S4: MCQ Generation<br/>Gemini 2.5 Flash Lite — Teacher]
        S4 --> S5[S5: Multi-Stage Validation<br/>Format → Relevance → Distractor → Dedup → LLM-Judge]
        S5 --> S6[S6: Dataset Construction<br/>Validated MCQs Only]
        S6 --> S7[S7: Dataset Audit<br/>Bloom Balance · Quality Check]
        S7 --> FT[LoRA Fine-Tuning<br/>QLoRA · Qwen2.5-1.5B-Instruct<br/>LLaMA-Factory]
        FT --> HF[Hugging Face Hub<br/>LoRA Adapter Deployment]
    end

    subgraph Runtime["Online — Runtime Inference"]
        R1[Document Upload] --> R2[Chunking + Metadata]
        R2 --> R3[Bloom Classification]
        R3 --> R4[Student Model Inference<br/>Qwen2.5-1.5B Fine-Tuned]
        R4 --> R5[MCQ Output<br/>Stem · Options · Answer · Metadata]
    end

    HF --> R4
```

### Knowledge Graph Pipeline

```mermaid
flowchart LR
    A[Chunked Text] --> B[LLM Entity Extraction<br/>Llama-3.1-8B-Instant]
    B --> C[Entity Types<br/>Name · Type · Description · Source]
    B --> D[Relationship Extraction<br/>PREREQUISITE_TO · BUILDS_UPON<br/>EXTENDS · USES · DEPENDS_ON · RELATED_TO]
    C --> E[Neo4j MERGE<br/>Idempotent Upsert]
    D --> E
    E --> F[Cross-Document Linking<br/>Second-Pass Graph Augmentation]
    F --> G[Subject Graph<br/>Multi-Document Knowledge Base]
    G --> H[Hop-Bounded Traversal<br/>Query → Seeds → Subgraph]
    H --> I[Structured Subgraph<br/>for LLM Context]
```

---

## 📁 Repository Structure


```
Agentic-AI-Tutor/
│
├── ai_service/                    # Python / FastAPI AI microservices
│   ├── rag/                       # Part A — RAG Tutor service
│   │   ├── chunk.py               # Document ingestion, OCR, semantic chunking
│   │   ├── kg_service.py          # Knowledge graph construction & traversal
│   │   ├── rag_service.py         # Hybrid retrieval, reranking, generation
│   │   ├── chunk_kg.py            # KG orchestration endpoint
│   │   └── models/                # Embedding & reranker model wrappers
│   ├── quiz/                      # Part B — Quiz generation service
│   │   ├── quiz_gen.py            # MCQ generation pipeline (S1–S5)
│   │   ├── validation.py          # Multi-stage validation & LLM-as-a-Judge
│   │   └── distillation/          # Dataset construction, LoRA fine-tuning (Kaggle notebooks)
│   └── main.py                    # FastAPI application entry point
│
├── Backend/                       # ASP.NET Core Web API
│   ├── Controllers/               # API controllers (Auth, Documents, Chat, Quiz, Subjects)
│   ├── Services/                  # Application services and background processors
│   ├── Models/                    # Entity Framework Core domain models
│   ├── Middleware/                # JWT auth, error handling, request logging
│   └── Program.cs                 # Application bootstrap & DI configuration
│
├── Frontend/                      # Presentation layer
│   └── web/                       # React web application
│       ├── src/pages/             # Login, Dashboard, Chat, Quiz, Subjects, Analytics
│       └── src/components/        # Shared UI components
│
├── screenshots/                   # UI screenshots (see Screenshot Guide above)
└── README.md
```

| Module | Responsibility |
|---|---|
| `ai_service/` | All AI and ML logic: document ingestion, embedding, BM25 indexing, KG construction, hybrid retrieval, reranking, answer generation, quiz generation, and validation. Exposed as a FastAPI microservice consumed exclusively by the backend. |
| `Backend/` | Application layer: user management, JWT authentication, per-user data isolation, document lifecycle management, session persistence, routing to the AI service, and structured API exposure to clients. |
| `Frontend/web/` | React web application. Communicates exclusively with the ASP.NET Core backend. |

---

## 🛠 Technology Stack

### Frontend

| Technology | Role | Justification |
|---|---|---|
| React | Web application | Component-based SPA for browser-based access |

### Backend

| Technology | Role |
|---|---|
| ASP.NET Core Web API | Application server, routing, business logic |
| Entity Framework Core | ORM for PostgreSQL relational layer |
| JWT Authentication | Stateless per-user authentication and authorization |
| Background Services | Async document processing and KG build orchestration |

### AI / ML

| Technology | Role |
|---|---|
| Python 3.11 + FastAPI | AI service hosting and API exposure |
| `intfloat/e5-base-v2` | Dense embedding model (768-dimensional) |
| `BAAI/bge-reranker-base` | Cross-encoder neural reranker |
| `Llama-3.1-8B-Instant` (Groq) | KG entity and relationship extraction |
| `Llama-3.3-70B-Versatile` (Groq) | Answer generation for RAG tutor |
| `Llama-3.3-70B` (Groq) | LLM-as-a-Judge MCQ quality scoring |
| `Google Gemini 2.5 Flash Lite` | Teacher model for MCQ dataset construction (offline only) |
| `Qwen2.5-1.5B-Instruct` + LoRA | Student model for runtime quiz generation |
| LLaMA-Factory | LoRA fine-tuning orchestration framework |
| OpenAI Whisper | Speech-to-text for voice query input |
| Tesseract OCR | Scanned document and embedded image OCR fallback |
| PyTorch + Transformers + PEFT | Model training and inference infrastructure |

### Databases

| Technology | Role |
|---|---|
| PostgreSQL + pgvector | Relational data, chunk storage, and HNSW-indexed dense vector search |
| Neo4j | Knowledge graph storage (entities, relationships, cross-document links) |

### Evaluation & Benchmarking

| Technology | Role |
|---|---|
| Natural Questions (NQ) | Retrieval and generation evaluation dataset (Part A) |
| HotpotQA | Multi-hop retrieval evaluation dataset (Part A) |
| BGE-Large | Semantic similarity metric for distillation evaluation (Part B) |
| SciPy / Statsmodels | Statistical significance testing (paired t-test, Wilcoxon, McNemar, bootstrap CI) |

---

## 🤖 AI Components

### RAG System (Part A)

The RAG system separates **offline knowledge preparation** from **online inference**.

During the **offline phase**, uploaded documents are parsed, cleaned (Unicode normalization, OCR artefact removal, boilerplate stripping), and segmented using adaptive semantic chunking with sentence-embedding similarity boundaries. Each chunk is embedded with `intfloat/e5-base-v2` and stored in PostgreSQL via pgvector with an HNSW cosine index. Simultaneously, entities and relationships are extracted by `Llama-3.1-8B-Instant` and persisted as a property graph in Neo4j, with a second pass constructing cross-document concept links within each subject.

During the **online phase**, user queries are resolved for conversational context, then processed through two parallel branches:
1. **Hybrid retrieval**: dense vector search + BM25 full-text search, fused with RRF (k=60)
2. **KG traversal**: entity NER → seed matching → hop-bounded graph expansion

The combined evidence is reranked by `BAAI/bge-reranker-base` and assembled into a structured context package for `Llama-3.3-70B-Versatile`, which generates citations, confidence scores, and the final answer.

### Hybrid Retrieval

```
RRF(d) = Σᵢ 1/(k + rᵢ(d)),   k = 60
```

Dense (E5 cosine similarity) and sparse (PostgreSQL FTS/BM25) rankings are fused via Reciprocal Rank Fusion. The unified pool is then passed to the cross-encoder reranker, limiting reranking cost to the bounded pool size.

### Knowledge Graph

Entities carry name, type, description, and source document. Relationships are typed from a controlled vocabulary: `PREREQUISITE_TO`, `BUILDS_UPON`, `EXTENDS`, `USES`, `DEPENDS_ON`, `RELATED_TO`. All writes use idempotent Neo4j `MERGE` operations batched with `UNWIND`, reducing round trips from O(N) to O(1) per batch. A cross-document augmentation pass links concepts across lecture files within the same subject, enabling multi-hop prerequisite reasoning.

### Knowledge Distillation Pipeline (Part B)

The distillation pipeline operates in two phases:

**Offline (dataset construction):** Documents are chunked and classified against Bloom's Taxonomy levels. Gemini 2.5 Flash Lite generates candidate MCQs through a slot-based prompt. Each candidate passes five validation gates:

| Stage | Check |
|---|---|
| S5-V1 | Format validation — schema compliance, option count, correct-answer field |
| S5-V2 | Relevance — answer must be grounded in the source chunk |
| S5-V3 | Distractor quality — plausible but clearly incorrect distractors |
| S5-V4 | Semantic deduplication — cosine similarity threshold against existing items |
| S5-V5 | LLM-as-a-Judge holistic score — CMQS ≥ acceptance threshold |

Only items passing all five gates enter the fine-tuning dataset.

**Online (fine-tuning):** Validated MCQs are used to fine-tune `Qwen2.5-1.5B-Instruct` with QLoRA via LLaMA-Factory. The resulting LoRA adapter is published to Hugging Face Hub and loaded by the quiz generation FastAPI service for zero-API-cost runtime inference.

### LLM-as-a-Judge (CMQS)

```
CMQS = 0.30·correctness + 0.20·clarity + 0.15·distractors + 0.15·educational_value + 0.20·chunk_grounding
```

Each dimension is scored 1–5 by `Llama-3.3-70B` (Groq). The composite score is used both for validation gating during dataset construction and as the primary metric in the three-tier evaluation framework.

### Voice Interaction

Speech-to-text uses OpenAI Whisper with audio pre-processing (noise reduction, silence trimming, format and duration validation). The transcribed text follows the identical retrieval and reasoning pipeline as text queries. Transcriptions are returned to the client for verification before submission.

---

## 📊 Evaluation Results

### Part A — Hybrid KG-RAG Retrieval

Evaluation was conducted on Natural Questions (NQ) and HotpotQA benchmarks (100 questions per dataset for the reranking subset).

| Configuration | NQ Hit@1 | NQ Hit@5 | NQ MRR | HotpotQA Hit@1 | HotpotQA Hit@5 |
|---|---|---|---|---|---|
| Dense-only baseline | — | — | — | — | — |
| + BM25 (hybrid) | ↑ | ↑ | ↑ | ↑ | ↑ |
| + Cross-Encoder Reranking | ↑↑ | ↑↑ | ↑↑ | ↑↑ | ↑↑ |
| + KG Integration (Hybrid KG-RAG) | ↑↑↑ | ↑↑↑ | ↑↑↑ | ↑↑↑ | ↑↑↑ |


**Ablation findings:**
- Adding BM25 hybrid retrieval provided significant lift over dense-only on both lexical and paraphrase queries.
- Cross-encoder reranking consistently improved Hit@1 and MRR over RRF alone.
- KG integration contributed most for multi-hop questions (HotpotQA), where graph traversal resolved relationships unavailable from chunk retrieval alone.

### Part A — End-to-End Generation Quality

Generation is evaluated on Exact Match (EM), Contain Match, Precision, Recall, F1, and Faithfulness across RAG-only, KG-only, and Hybrid KG-RAG configurations on NQ and HotpotQA.


### Part B — Knowledge Distillation Results

| Model | CMQS (avg) | Bloom Accuracy | Semantic Sim. (BGE-Large) |
|---|---|---|---|
| Teacher (Gemini 2.5 Flash Lite) | Reference | Reference | 1.00 |
| Base Qwen2.5-1.5B (Pre-FT) | Significantly lower | Low | Low |
| Fine-Tuned Qwen2.5-1.5B (V8 Post-FT) | Substantially recovered | Improved | High |

**Key findings (V8 fine-tuning run):**
- Fine-tuning produced a statistically significant improvement over the pre-FT baseline across all CMQS dimensions (paired t-test, Wilcoxon, McNemar, bootstrap CI).
- The largest absolute gains were in `correctness` and `chunk_grounding`.
- KL divergence between student and teacher output distributions decreased substantially post-fine-tuning.
- The Retention Score (RS = QPS × latency_teacher / latency_student) confirmed that the student model delivers competitive quality at significantly lower inference latency.


### Part B — Validation Pipeline Performance

| Validation Stage | Pass Rate |
|---|---|
| S5-V1: Format | High — schema enforcement effective |
| S5-V2: Relevance | Majority pass after format filtering |
| S5-V3: Distractor Quality | Moderate filtering; primary quality gate |
| S5-V4: Deduplication | Low removal rate — dataset diversity maintained |
| S5-V5: LLM-as-a-Judge | Most discriminating gate; rejects marginal items |


---

## 🔌 API Overview

### ASP.NET Core Backend (selected endpoints)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | User registration |
| `POST` | `/api/auth/login` | JWT token issuance |
| `POST` | `/api/documents/upload` | Upload document to subject library |
| `GET` | `/api/documents/{subjectId}` | List documents for a subject |
| `POST` | `/api/chat/ask` | Submit text query; returns RAG answer + citations |
| `POST` | `/api/chat/audio` | Submit voice query (STT → RAG pipeline) |
| `GET` | `/api/chat/history/{sessionId}` | Retrieve conversation history |
| `POST` | `/api/quiz/generate` | Request MCQ generation from document(s) |
| `GET` | `/api/quiz/{quizId}` | Retrieve a stored quiz |
| `POST` | `/api/quiz/{quizId}/submit` | Submit quiz answers for scoring |
| `GET` | `/api/subjects` | List user subjects |
| `POST` | `/api/subjects` | Create a new subject |
| `GET` | `/api/kg/status/{documentId}` | Knowledge graph build lifecycle status (PROCESSING / COMPLETED / FAILED) |

### Python FastAPI AI Service (selected endpoints)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Trigger document ingestion, chunking, embedding |
| `POST` | `/chunk_kg` | Orchestrate KG construction for a document |
| `POST` | `/query` | Execute hybrid RAG query; return answer + citations |
| `POST` | `/quiz/generate` | Generate MCQs from specified chunks |
| `GET` | `/health` | Service health check |

---

## 🚀 Installation

### Prerequisites

- Python 3.11+
- .NET 8 SDK
- Node.js 20+ and npm (for React web)
- PostgreSQL 15+ with pgvector extension
- Neo4j 5.x
- Docker (optional, for containerized deployment)

### 1. AI Service (Python / FastAPI)

```bash
# Clone the repository
git clone https://github.com/Rehab-Hamdy/Agentic-AI-Tutor.git
cd Agentic-AI-Tutor/ai_service

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Set the following in .env:
# GROQ_API_KEY=<your_groq_api_key>
# GOOGLE_API_KEY=<your_gemini_api_key>          # offline dataset construction only
# OPENAI_API_KEY=<your_openai_key>              # Whisper STT
# POSTGRES_URL=postgresql://user:pass@localhost:5432/gent_db
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=<your_neo4j_password>

# Run database migrations (pgvector extension)
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Start the FastAPI service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Backend (ASP.NET Core)

```bash
cd ../Backend

# Configure connection strings and API endpoints
# Edit appsettings.json or use environment variables:
# ConnectionStrings__DefaultConnection = <postgres connection string>
# AIService__BaseUrl = http://localhost:8001
# JWT__SecretKey = <your_jwt_secret>

# Restore packages and run migrations
dotnet restore
dotnet ef database update

# Start the backend
dotnet run --project GenT.Api
# API available at https://localhost:5001
```

### 3. React Web App

```bash
cd ../Frontend/web

# Install npm dependencies
npm install

# Configure backend URL
cp .env.example .env.local
# VITE_API_BASE_URL=https://localhost:5001

# Start development server
npm run dev
# Web app available at http://localhost:5173
```

---

## ▶️ Running the Full System Locally

```bash
# Terminal 1 — Start Neo4j (or use Neo4j Desktop)
neo4j start

# Terminal 2 — Start PostgreSQL (ensure pgvector is installed)
pg_ctl start

# Terminal 3 — Start the Python AI service
cd ai_service && source venv/bin/activate && uvicorn main:app --port 8001

# Terminal 4 — Start the ASP.NET Core backend
cd Backend && dotnet run --project GenT.Api

# Terminal 5 — Start the React web client
cd Frontend/web && npm run dev
```

Access the web interface at `http://localhost:5173`. The backend API documentation (Swagger) is available at `https://localhost:5001/swagger`.

---

## 🔮 Future Improvements

Based on the limitations identified during evaluation and the recommendations in the project thesis:

**Advanced Educational Personalisation**
- Learner knowledge-state modelling with spaced-repetition scheduling
- Adaptive difficulty adjustment based on quiz performance history
- Personalised prerequisite pathways from the knowledge graph

**Advanced Agentic RAG**
- Multi-step query decomposition and iterative retrieval loops
- Tool-augmented reasoning: calculator, code interpreter, external knowledge APIs
- Self-reflective generation with automated answer quality assessment

**Enhanced Quiz Generation**
- Support for open-ended, short-answer, and fill-in-the-blank question types
- Difficulty calibration using Item Response Theory (IRT)
- Feedback generation aligned to incorrect option selection

**Multimodal Educational Intelligence**
- Native understanding of embedded diagrams, equations, and figures
- Vision-language model integration for PPTX-heavy course materials

**Continuous Learning & Feedback Loops**
- Human-in-the-loop correction of hallucinated answers for retrieval improvement
- Student interaction data used to iteratively improve the quiz generation model

**Scalability & Production Deployment**
- Kubernetes orchestration for horizontal scaling of stateless AI workers
- Asynchronous job queuing for document ingestion (Celery / RabbitMQ)
- Caching layer for frequent embedding lookups

---

## 👥 Team

Developed as a graduation project at the **Faculty of Computers & Artificial Intelligence, Capital University (formerly Helwan University)**, under the supervision of **Dr. Amr S. Ghoneim**.

| Name | Role | GitHub |
|---|---|---|
| Rehab Hamdy Abdallah | Team Lead · AI Engineer | [Rehab-Hamdy](https://github.com/Rehab-Hamdy) |
| Aya Khaled Farouk | AI Engineer | [Yota-khaled](https://github.com/Yota-khaled) |
| Aya Mohamed Abdelfatah | AI Engineer | [aya2500](https://github.com/aya2500) |
| Shahd Elsayed Ahmed | AI Engineer | [shahdooz17](https://github.com/shahdooz17) |
| Ahmed Maghawry | Full Stack Developer | [Ahmedmaghawry679](https://github.com/Ahmedmaghawry679) |
| Abdelrahman Mohamed Abdellatif | Mobile Frontend Developer |  |
---

## 🙏 Acknowledgements

This system was developed as a graduation project submitted in partial fulfilment of the requirements for the **Bachelor of Science in Computers & Artificial Intelligence** at the Computer Science and Artificial Intelligence Departments, Faculty of Computers & Artificial Intelligence, Capital University (formerly Helwan University), June 2026.

We extend our sincere gratitude to **Dr. Amr S. Ghoneim** for invaluable guidance, unwavering support, and constructive feedback throughout the design and evaluation of both subsystems.

We also thank the Faculty of Computers & Artificial Intelligence and the Artificial Intelligence and Computer Science Departments for the academic environment and infrastructure that made this work possible.

---

<div align="center">

**GenT — AI Tutor Assistant**  
*Hybrid KG-RAG Educational Assistant · Bloom's Taxonomy Quiz Generation*  
Capital University · June 2026

</div>