# Agentic AI Tutor — Running and Trying the Project

This project is a full-stack AI tutoring system built from three parts:

- Python AI service: document ingestion, embedding, KG + RAG, voice, and quiz generation
- ASP.NET Core backend: authentication, file/document management, orchestration, and API layer
- React frontend: student dashboard and chat/quiz UI

The repo is organized as:

- [ai_service](ai_service)
- [Backend/AgenticAITutor/AgenticAITutor](Backend/AgenticAITutor/AgenticAITutor)
- [Frontend](Frontend)
- [README.md](README.md)

---

## 1) Prerequisites

Install the following before starting:

- Python 3.11+
- .NET 8 SDK
- Node.js 20+ and npm
- PostgreSQL 15+ with pgvector
- Neo4j 5.x
- Git
- Optional: Docker, if you want to manage database services there

You will also need API keys for external AI services:

- Groq API key
- OpenAI API key (for Whisper/STT)
- Google Gemini API key (used for quiz generation dataset creation and related offline AI workflows)

> The project currently does not include committed production app settings or secrets. You must create local configuration files for the Python service, .NET backend, and frontend.

---

## 2) Suggested local architecture

Use these local ports during setup:

- Python AI service: http://localhost:8001
- .NET backend: http://localhost:5099
- React frontend: http://localhost:5173
- PostgreSQL: localhost:5432
- Neo4j: bolt://localhost:7687

The backend code defaults to AI service calls at http://localhost:8000 in some places, but the project README and the FastAPI app setup point to port 8001. It is safer to explicitly set the backend config to 8001 and keep the service on that port.

---

## 3) Set up PostgreSQL with pgvector

### Install and start PostgreSQL

On Windows, either:

- install PostgreSQL locally and start the database service, or
- run it via Docker if preferred

### Create the database and extension

```sql
CREATE DATABASE AgenticAITutor;
\c AgenticAITutor
CREATE EXTENSION IF NOT EXISTS vector;
```

You can also use a connection string like:

```text
Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=your_password
```

---

## 4) Set up Neo4j

Install Neo4j Desktop or run Neo4j locally.

Typical connection values:

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

The app initializes the KG schema at startup, so Neo4j should be reachable before starting the Python service.

---

## 5) Configure the Python AI service

Go to the AI service folder:

```bash
cd ai_service
```

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file named `.env` in [ai_service](ai_service):

```env
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
POSTGRES_URL=postgresql://postgres:your_password@localhost:5432/AgenticAITutor
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

For multilingual **Listen** playback, the AI service uses `GOOGLE_API_KEY` for Gemini TTS when the browser has no voice for the selected language. To use a separate key, set `GEMINI_TTS_API_KEY`. Optional overrides are `GEMINI_TTS_MODEL` (defaults to `gemini-3.8-flash-lite-tts`) and `GEMINI_TTS_VOICE` (defaults to `Kore`). Keep these values in the AI service environment, never in the frontend.

Start the FastAPI app:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Check the app is alive:

```bash
http://localhost:8001/docs
```

This FastAPI app is the AI layer that exposes the RAG and quiz routes.

---

## 6) Configure the .NET backend

Open the backend project folder:

```bash
cd Backend/AgenticAITutor/AgenticAITutor
```

The backend project is the ASP.NET Core API in [Backend/AgenticAITutor/AgenticAITutor](Backend/AgenticAITutor/AgenticAITutor). The project uses `launchSettings.json` and expects local configuration values for DB and AI service endpoints.

### Create local config

Create a file named `appsettings.Development.json` in the project folder with a structure like:

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=your_password"
  },
  "JWT": {
    "Key": "replace-with-a-long-random-secret-key",
    "Issuer": "AgenticAITutor",
    "Audience": "AgenticAITutorUsers",
    "DurationInDays": 7
  },
  "AIService": {
    "BaseURL": "http://localhost:8001"
  },
  "AppConfig": {
    "BaseURL": "http://localhost:5099"
  }
}
```

You can also use environment variables instead of a file, but the project code clearly expects `ConnectionStrings__DefaultConnection`, `JWT__Key`, and `AIService__BaseURL` values.

### Restore and run

```bash
dotnet restore
dotnet run
```

The app will start using the port from [Backend/AgenticAITutor/AgenticAITutor/Properties/launchSettings.json](Backend/AgenticAITutor/AgenticAITutor/Properties/launchSettings.json), which is currently:

- http://localhost:5099
- https://localhost:7257

Swagger UI should be available at:

```text
http://localhost:5099/swagger
```

---

## 7) Configure the React frontend

Go to the frontend folder:

```bash
cd Frontend
npm install
```

Create a `.env.local` file in [Frontend](Frontend):

```env
VITE_API_BASE_URL=http://localhost:5099
```

Start the UI:

```bash
npm run dev
```

The app should open at:

```text
http://localhost:5173
```

The frontend code in [Frontend/src/lib/apiClient.ts](Frontend/src/lib/apiClient.ts) and [Frontend/src/services/documentService.ts](Frontend/src/services/documentService.ts) defaults to `http://localhost:5099` if no environment variable is provided.

---

## 8) Run everything together

Use 5 terminals in parallel:

### Terminal 1 — Neo4j

```bash
neo4j start
```

### Terminal 2 — PostgreSQL

```bash
pg_ctl start
```

### Terminal 3 — Python AI service

```bash
cd ai_service
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 4 — .NET backend

```bash
cd Backend/AgenticAITutor/AgenticAITutor
dotnet restore
dotnet run
```

### Terminal 5 — React frontend

```bash
cd Frontend
npm install
npm run dev
```

---

## 9) How to try the app

Once all services are up:

1. Open http://localhost:5173
2. Register a new user account
3. Log in with the new credentials
4. Create a subject
5. Upload a PDF, DOCX, PPTX, TXT, or CSV document
6. Wait for the backend and AI service to process the file
7. Open the subject/chat area
8. Ask a question related to the uploaded material
9. Check the answer, citations, and knowledge graph-related context
10. Generate a quiz from the same document
11. Take the quiz and review results

---

## 10) Important notes about the project

### This app is not a simple single-command startup

The repo depends on multiple external services and model providers. Without the services running and without the proper local config, the app will fail at runtime.

### Some features require API keys

The AI service relies on Groq/OpenAI/Gemini for retrieval and generation. If keys are missing, you may be able to start the app, but document processing and AI answers will not work correctly.

### The backend and Python service must agree on the port

The backend code reads `AIService:BaseURL`; set it to the actual FastAPI URL. The project README says port `8001`, while some backend code default values mention `8000`. Use one consistent value and keep the config aligned.

### Frontend must point to the backend

Set `VITE_API_BASE_URL` to the .NET server URL so the browser calls the correct API host.

---

## 11) Quick troubleshooting

### The frontend loads but login/register fails

- confirm the .NET backend is running on localhost:5099
- check your JWT config values in `appsettings.Development.json`
- verify PostgreSQL is running and the database exists

### Document upload fails or hangs

- confirm the FastAPI service is running on port 8001
- check Groq/OpenAI/Gemini API keys
- verify PostgreSQL and Neo4j are reachable

### Swagger/HTTP errors from backend

- check `ConnectionStrings__DefaultConnection`
- check `AIService__BaseURL`
- check `AppConfig__BaseURL`

### The AI service refuses to start

- install all requirements from [ai_service/requirements.txt](ai_service/requirements.txt)
- ensure Python 3.11+ is being used
- check that Neo4j and PostgreSQL are up before starting the app

---

## 12) Recommended first test flow

For a first smoke test:

1. Start Neo4j
2. Start PostgreSQL and ensure the `AgenticAITutor` database exists
3. Start AI service on port 8001
4. Start .NET backend on 5099
5. Start frontend on 5173
6. Create a new user
7. Create one subject
8. Upload a small text or PDF file
9. Ask a short question like: "What is the main topic of this document?"
10. Generate a quiz from the uploaded content

If all steps work, the project is running correctly end-to-end.

---

## 13) Related project files

- [README.md](README.md) — project overview and architecture
- [ai_service/requirements.txt](ai_service/requirements.txt) — Python dependencies
- [Backend/AgenticAITutor/AgenticAITutor/Properties/launchSettings.json](Backend/AgenticAITutor/AgenticAITutor/Properties/launchSettings.json) — backend ports
- [Frontend/src/lib/apiClient.ts](Frontend/src/lib/apiClient.ts) — frontend API base URL
- [Frontend/package.json](Frontend/package.json) — frontend scripts
- [ai_service/app/main.py](ai_service/app/main.py) — FastAPI app registration

This guide should be enough to get the project running locally and to test the end-to-end tutor workflow.
