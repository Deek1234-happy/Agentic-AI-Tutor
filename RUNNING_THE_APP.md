# Running GenT Locally on Windows

This guide covers the complete local stack in this repository: the React frontend, ASP.NET Core API, Python AI service, PostgreSQL with pgvector, and Neo4j.

## Service URLs and ports

| Component | Local address | Notes |
|---|---|---|
| Web application | http://localhost:5173 | Open this in your browser |
| ASP.NET Core API | http://localhost:5099 | The `http` launch profile |
| ASP.NET Core Swagger | http://localhost:5099/swagger | API documentation |
| Python AI service | http://localhost:8001 | FastAPI service |
| FastAPI Swagger | http://localhost:8001/docs | AI service API documentation |
| PostgreSQL | `localhost:5433` | The project uses this port for its Docker database |
| Neo4j Browser | http://localhost:7474 | Browser UI; Bolt connection is `bolt://localhost:7687` |

## Prerequisites

Install or have available:

- Windows 10/11 and PowerShell.
- Python 3.11. The AI dependencies include Torch and TTS; use the project's Python 3.11 environment rather than a newer Python release.
- .NET 8 SDK.
- Node.js 20 or later and npm.
- Docker Desktop, for the PostgreSQL and Neo4j containers.
- LLM provider API keys for the features you intend to use. This checkout is configured to use Gemini for chat, knowledge-graph extraction, and quiz generation. Speech, web-search, and other provider features may need their own keys.

The commands below assume the repository is at:

```text
C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor
```

If yours is elsewhere, replace that path in each terminal command.

## First-time setup

### 1. Configure the databases

Start Docker Desktop. This checkout has PostgreSQL and Neo4j Docker containers named `agenticai-pg` and `agenticai-neo4j`. Start them from PowerShell:

```powershell
docker start agenticai-pg agenticai-neo4j
```

If Docker reports that those containers do not exist on your machine, create equivalent containers and choose your own strong passwords:

```powershell
docker run -d --name agenticai-pg `
  -e POSTGRES_DB=agenticaitutor `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD="<choose-a-postgres-password>" `
  -p 5433:5432 `
  -v agenticai-pg-data:/var/lib/postgresql/data `
  pgvector/pgvector:pg17

docker run -d --name agenticai-neo4j `
  -p 7474:7474 -p 7687:7687 `
  -e NEO4J_AUTH="neo4j/<choose-a-neo4j-password>" `
  -v agenticai-neo4j-data:/data `
  neo4j:5
```

For a **new, empty PostgreSQL database only**, initialize the application's tables from the repository schema. Do not run this against a database that already contains application data: the script creates tables and is not a reset/upgrade command.

```powershell
docker cp "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\Backend\AgenticAITutor\AgenticAITutor\schema.sql" agenticai-pg:/tmp/gent-schema.sql
docker exec agenticai-pg psql -U postgres -d agenticaitutor -f /tmp/gent-schema.sql
```

The application configuration must use the same database names, ports, usernames, and passwords as your containers:

- `Backend\AgenticAITutor\AgenticAITutor\appsettings.json`: `ConnectionStrings:DefaultConnection` and `AIService:BaseURL`.
- `ai_service\.env`: `DATABASE_URL`, `POSTGRES_URL`, `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.

Use port `5433` for the host-side PostgreSQL connection (Docker maps it to container port `5432`). `DATABASE_URL` and `POSTGRES_URL` should both point to that same database. The AI service reads `DATABASE_URL`; other AI modules may read `POSTGRES_URL`.

### 2. Configure the AI service

Create or edit `ai_service\.env` (there is no `.env.example` in this checkout). Keep credentials private; do not commit this file or paste real keys into source code. At minimum, configure the database and graph values as above and provide the keys required by the selected providers:

```dotenv
DATABASE_URL=postgresql://postgres:<URL-encoded-password>@localhost:5433/agenticaitutor
POSTGRES_URL=postgresql://postgres:<URL-encoded-password>@localhost:5433/agenticaitutor
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-neo4j-password>

CHAT_LLM_PROVIDER=gemini
KG_LLM_PROVIDER=gemini
QUIZ_LLM_PROVIDER=gemini
GEMINI_CHAT_API_KEY=<your-chat-key>
GEMINI_KG_API_KEY=<your-knowledge-graph-key>
GEMINI_QUIZ_API_KEY=<your-quiz-key>
GEMINI_TTS_API_KEY=<your-text-to-speech-key>
```

If a PostgreSQL password contains URL-reserved characters, URL-encode it in both PostgreSQL URLs. Set only the provider keys/features you plan to use. For example, voice transcription may require `OPENAI_API_KEY`; web search may require `TAVILY_API_KEY`. `GOOGLE_API_KEY` can be used as a shared Gemini fallback where supported by the service.

Create and install the Python environment once:

```powershell
Set-Location "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\ai_service"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, install packages without activating it:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The run command below also uses the environment's interpreter directly. Do not weaken machine-wide PowerShell execution policy just for this project.

### 3. Restore the .NET and frontend packages

Run each set of commands once:

```powershell
Set-Location "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\Backend\AgenticAITutor\AgenticAITutor"
dotnet restore
```

```powershell
Set-Location "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\Frontend"
npm install
```

The frontend defaults to the API at `http://localhost:5099`. If you need a different API URL, create `Frontend\.env.local` with:

```dotenv
VITE_API_BASE_URL=http://localhost:5099
```

Restart the Vite server after changing frontend environment variables.

## Start the complete application

Start Docker Desktop first, then run the following in **four separate PowerShell terminals**. Keep each terminal open while using the app; `Ctrl+C` stops the process in that terminal.

### Terminal 1 — databases

```powershell
docker start agenticai-pg agenticai-neo4j
```

If they are already running, Docker reports that they are started.

### Terminal 2 — Python AI service

```powershell
Set-Location "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\ai_service"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Wait for Uvicorn to report that it is running before starting the API. Run this from the `ai_service` directory so the service finds `.env` and its `static` directory.

### Terminal 3 — ASP.NET Core API

```powershell
Set-Location "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\Backend\AgenticAITutor\AgenticAITutor"
dotnet run --launch-profile http
```

This uses the repository's `http` launch profile and serves the API on port `5099`.

### Terminal 4 — React frontend

```powershell
Set-Location "C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\Frontend"
npm run dev
```

Open **http://localhost:5173** in your browser. Register or sign in from the landing page. The first AI request may take longer while local ML models are downloaded or initialized.

## Confirm that services are ready

In a separate PowerShell window:

```powershell
docker ps
Test-NetConnection localhost -Port 5433
Test-NetConnection localhost -Port 7687
Invoke-WebRequest http://localhost:5173/ -UseBasicParsing
Invoke-WebRequest http://localhost:5099/swagger/index.html -UseBasicParsing
Invoke-WebRequest http://localhost:8001/openapi.json -UseBasicParsing
```

The two `Test-NetConnection` results should show `TcpTestSucceeded : True`; each HTTP request should return a successful response. You can also open the Swagger pages listed above.

## Stop and restart

- Stop an app process with `Ctrl+C` in its terminal.
- Stop the database containers when you no longer need them with `docker stop agenticai-pg agenticai-neo4j`. This does not delete their persistent Docker volumes.
- On the next run, start Docker Desktop, run `docker start agenticai-pg agenticai-neo4j`, and start the AI service, API, and frontend in their separate terminals.

## Troubleshooting

- **Port already in use:** Check that only one copy of each app server is running. The frontend uses `5173`, the API uses `5099`, the AI service uses `8001`, and the configured PostgreSQL host port is `5433`.
- **Database connection refused:** Confirm Docker Desktop is running and `docker ps` lists both database containers. PostgreSQL must be reachable at `localhost:5433`, not merely a local PostgreSQL installation on `5432`.
- **AI service fails during startup:** Run from `ai_service`, check that `.env` exists and contains `DATABASE_URL`, and confirm the Python environment is Python 3.11 with the requirements installed.
- **Gemini or another AI feature reports a key/provider error:** Check the matching provider selection and API key in `ai_service\.env`; restart Uvicorn after editing `.env`.
- **New database has missing tables:** Apply `schema.sql` once to the new, empty database as described above. Do not apply it to an existing database as a routine startup step.
- **Vite opens a different port:** If port `5173` is occupied, Vite may choose another one. Use the URL printed by Vite; the backend URL remains `http://localhost:5099`.

## Current checkout status

When this guide was prepared, the frontend, API, AI service, PostgreSQL/pgvector, and Neo4j were already running locally. The web page was reachable at http://localhost:5173, the API Swagger page at http://localhost:5099/swagger, and the AI API schema at http://localhost:8001/openapi.json. PostgreSQL and Neo4j connectivity were also verified.
