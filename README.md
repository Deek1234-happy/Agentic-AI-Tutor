# Agentic-AI-Tutor

An intelligent AI-powered tutoring system built with FastAPI that combines Retrieval Augmented Generation (RAG), Knowledge Graphs, and voice capabilities to provide personalized educational experiences.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Set Up Virtual Environment](#step-2-set-up-virtual-environment)
  - [Step 3: Install Dependencies](#step-3-install-dependencies)
  - [Step 4: Configure Environment Variables](#step-4-configure-environment-variables)
  - [Step 5: Set Up Database](#step-5-set-up-database)
  - [Step 6: Additional Setup](#step-6-additional-setup)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)

## Features

- **Retrieval Augmented Generation (RAG)**: Grounds AI responses with actual document content
- **Knowledge Graph Processing**: Extracts entities and relationships from documents using Neo4j
- **Multi-format Document Support**: Process PDF, Word (.docx), PowerPoint (.pptx), and text files
- **Voice Integration**: Text-to-Speech (TTS) and Speech-to-Text (STT) capabilities
- **Web Search Chat**: Integration with web search for extended knowledge
- **Vector Embeddings**: Fast semantic search using sentence-transformers and FAISS
- **OCR Support**: Extract text from scanned documents using Tesseract
- **Evaluation Framework**: Built-in evaluation and quality assessment tools
- **Knowledge Management**: Store and query educational content efficiently

## Installation

### Prerequisites

Before starting, ensure you have the following installed:

1. **Python 3.9+**: [Download here](https://www.python.org/downloads/)
2. **Git**: [Download here](https://git-scm.com/)
3. **PostgreSQL 12+**: [Download here](https://www.postgresql.org/download/) (for database storage)
4. **Neo4j 4.4+**: [Download here](https://neo4j.com/download/) (for knowledge graph)
5. **Tesseract OCR** (optional, for PDF extraction):
   - **Windows**: Download from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

### Step 1: Clone the Repository

```bash
cd path/to/your/workspace
git clone <repository-url>
cd Agentic-AI-Tutor
```

### Step 2: Set Up Virtual Environment

Create and activate a Python virtual environment:

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
cd ai_service
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the `ai_service` directory with the following configuration:

```bash
# .env file template
# Copy this to ai_service/.env and fill in your values

SIMILARITY_THRESHOLD = 0.5

EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# ============================================================
# LLM Configuration (Groq API)
# ============================================================
LLM_API_KEY=your_groq_api_key_here
LLM_URL=https://api.groq.com/openai/v1/chat/completions
LLM_MODEL=llama3-70b-8192

# ============================================================
# Neo4j Configuration (Knowledge Graph Database)
# ============================================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ============================================================
# PostgreSQL Configuration (Content Storage)
# ============================================================
DATABASE_URL=postgresql://username:password@localhost:5432/agentic_ai_tutor

# ============================================================
# Web Search Configuration
# ============================================================
TAVILY_API_KEY=your_api_key_here
OPENROUTER_API_KEY=your_api_key_here

USE_OPTIMIZED_KG=True

# Groq Configuration (1000 requests/day FREE!)
GROQ_API_KEY=your_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
```

**Getting API Keys:**

1. **Groq API Key**: [Sign up at Groq Console](https://console.groq.com)
2. **Neo4j Database**: Use default credentials or create a new one

### Step 5: Set Up Database

#### PostgreSQL Setup

```bash
# Create database
createdb agentic_ai_tutor

# Or using psql:
psql -U postgres
CREATE DATABASE agentic_ai_tutor;
```

#### Neo4j Setup

1. **Start Neo4j Desktop**:
   Open Neo4j Desktop and create a new project.

2. **Access Neo4j Browser**: http://localhost:7474
3. **Set your password** (default is `neo4j`/`password`)

### Step 6: Additional Setup

#### For Tesseract OCR (Optional)

**Windows:**

- Download installer from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Install and note the installation path
- Update your `.env` or system PATH if needed

**macOS:**

```bash
brew install tesseract
```

**Linux:**

```bash
sudo apt-get install tesseract-ocr
```

#### Download TTS Models

The TTS models will be downloaded automatically on first use. This may take a few minutes:

## Running the Application

### Start the FastAPI Server

```bash
cd ai_service
uvicorn app.main:app --reload
```

**Output:**

```
INFO:     Uvicorn running on http://8000
INFO:     Application startup complete
```

### Access the Application

- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Verify Setup

Test the installation by making a simple API call:

```bash
curl http://localhost:8000/docs
```

## Project Structure

```
Agentic-AI-Tutor/
├── ai_service/                    # Main AI service
│   ├── app/
│   │   ├── main.py               # FastAPI application entry point
│   │   ├── chat.py               # Chat service endpoints
│   │   ├── rag.py                # RAG pipeline
│   │   ├── kg_service.py         # Knowledge graph management
│   │   ├── extraction.py         # Document extraction
│   │   ├── embedding.py          # Vector embeddings
│   │   ├── vector_store.py       # FAISS vector store
│   │   ├── llm.py                # LLM interface
│   │   ├── audio/
│   │   │   ├── tts.py            # Text-to-speech
│   │   │   ├── stt.py            # Speech-to-text
│   │   │   └── models/           # Pre-trained models
│   │   ├── evaluation/           # Evaluation framework
│   │   └── test_files/           # Sample test files
│   ├── static/                    # Static files
│   ├── temp/                      # Temporary files
│   ├── requirements.txt          # Python dependencies
│   └── __init__.py
├── data/
│   ├── chunks/                    # Vectorized chunks
│   └── uploads/                   # Uploaded files
├── temp/                          # Application temp storage
└── temp_audio/                    # Audio processing temp files
```
