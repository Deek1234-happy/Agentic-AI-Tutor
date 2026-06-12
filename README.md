#  GenT AI Tutor — Backend API

**Branch:** `Backend` &nbsp;|&nbsp; **Role:** ASP.NET Core Web API (Backend)

> A production-ready backend that powers an intelligent tutoring system. Students can upload study documents, converse with an AI tutor grounded in those documents, run live web searches, generate quizzes, track progress analytics, and convert speech to text and back.

**Core Tech Stack:** ASP.NET Core 8 · PostgreSQL 15 + pgvector · Entity Framework Core · Hangfire · JWT Auth · FluentValidation · Swagger/OpenAPI

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Architecture](#-architecture)
3. [Project Structure](#️-project-structure)
4. [API Controllers](#-api-controllers)
5. [Data Models](#️-data-models)
6. [Background Jobs](#️-background-jobs-hangfire)
7. [Prerequisites](#-prerequisites)
8. [Configuration](#-configuration)
9. [Installation & Setup](#-installation--setup)
10. [Running the Application](#-running-the-application)
11. [Feature Setup Guides](#-feature-setup-guides)
12. [API Documentation](#-api-documentation)

---

## 🧭 Overview

The **Agentic AI Tutor Backend** is a layered ASP.NET Core 8 Web API that acts as the central orchestration layer between the frontend, a PostgreSQL database, and an external Python AI microservice. Its responsibilities include:

- **Identity & Access Management** — JWT-based registration, login, and password management (OTP-based forgot-password flow).
- **Content Management** — Upload and organize study documents (PDF, DOCX, TXT, PPTX) into subjects.
- **Retrieval-Augmented Generation (RAG)** — Chunk documents into vector embeddings and route chat queries to the AI service.
- **Knowledge Graph (KG)** — Maintains a graph of concepts derived from uploaded documents; cleaned up on document/subject deletion.
- **Quiz Engine** — AI-generated quizzes with server-side shuffling, idempotent submission, and a full review mode.
- **Progress Analytics** — Aggregates quiz attempt history via EF Core into KPIs, monthly trends, subject scores, and weak-concept identification for a frontend Recharts dashboard.
- **Voice I/O** — Speech-to-Text (STT) and Text-to-Speech (TTS) via the Python microservice.

---

## 📐 Architecture

The system is composed of two runtime processes that communicate over HTTP:

```text
┌──────────────────────────────────────────────────────────────────┐
│                      ASP.NET Core Web API                        │
│                                                                  │
│   HTTP Request                                                   │
│       │                                                          │
│       ▼                                                          │
│   Controllers  ──►  Services  ──►  Repositories  ──►  PostgreSQL │
│                                                                  │
│                         │                                        │
│                         ▼                                        │
│              Hangfire Background Jobs                            │
│               (DocumentChunkingJob, QuizGenerationJob)           │
│                         │                                        │
│                         ▼                                        │
│         Python AI Microservice  (external HTTP)                  │
│   ┌─────────────┬──────────────┬──────────────────────────────┐  │
│   │  /chat      │ /web-search  │  /extract/embed              │  │
│   │  /audio/stt │ /audio/tts   │  /kg/subject  /kg/document   │  │
│   └─────────────┴──────────────┴──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Communication contract:** The .NET API enqueues long-running work (document chunking, quiz generation) as Hangfire jobs to avoid blocking HTTP request threads. All calls to the Python service are made from within those background jobs or from scoped services using named `HttpClient` instances registered at startup — ensuring thread safety and preventing header mutation race conditions.

---

## 🗂️ Project Structure

```text
AgenticAITutor/
│
├── Controllers/               # HTTP endpoints
│   ├── AnalyticsController.cs #   Progress & KPI dashboard
│   ├── AuthController.cs      #   Registration, login, password management
│   ├── ChatMessageController.cs #  RAG chat, web search, STT, TTS
│   ├── ChatSessionController.cs #  Session lifecycle
│   ├── DocumentChunkController.cs # Vector chunk inspection
│   ├── DocumentController.cs  #   Document upload & management
│   ├── QuizController.cs      #   Quiz lifecycle (initiate → start → submit → review)
│   ├── SubjectController.cs   #   Subject CRUD
│   └── UserController.cs      #   User profile management
│
├── Services/                  # Business logic layer
├── Repositories/              # Data access layer (EF Core)
├── Models/
│   ├── (entity classes)       # EF Core database models (scaffolded)
│   └── DTOs/                  # Request / Response data-transfer objects
├── BackgroundJobs/            # Hangfire job definitions
│   ├── DocumentChunkingJob.cs
│   └── QuizGenerationJob.cs
├── Data/                      # AppDbContext + AppDbContext_Partial.cs (vector config)
├── Validators/                # FluentValidation rule sets
├── Extensions/                # ClaimsPrincipal helpers (GetUserId)
├── Middlewares/               # Custom ASP.NET Core middleware
├── Filters/                   # Hangfire dashboard authorization filter
├── Helpers/                   # JWT config class
├── wwwroot/
│   └── uploads/               # Uploaded files (gitignored)
├── appsettings.json           # Production configuration (never commit secrets)
├── appsettings.Development.json # Local dev overrides
└── Program.cs                 # DI registrations & middleware pipeline
```

---

## 📡 API Controllers

All endpoints except `POST /api/auth/register` and `POST /api/auth/login` require a **JWT Bearer token** in the `Authorization` header.

### AuthController — `/api/auth`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `POST` | `/api/auth/register` | ❌ | Register a new user account; returns a JWT token |
| `POST` | `/api/auth/login` | ❌ | Authenticate with email & password; returns a JWT token |
| `POST` | `/api/auth/forgot-password` | ❌ | Generate a 6-digit OTP and send it to the user's email (expires in 15 minutes) |
| `POST` | `/api/auth/reset-password` | ❌ | Validate the OTP and set a new password |
| `POST` | `/api/auth/change-password` | ✅ | Change the currently authenticated user's password (requires current password) |

---

### UserController — `/api/user`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `GET` | `/api/user/profile` | ✅ | Retrieve the authenticated user's profile (`FirstName`, `LastName`, `Email`) |
| `PUT` | `/api/user/profile` | ✅ | Update the authenticated user's profile data |
| `DELETE` | `/api/user/profile` | ✅ | Permanently delete the authenticated user's account |

---

### AnalyticsController — `/api/Analytics`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `GET` | `/api/Analytics/progress` | ✅ | Returns a `ProgressDashboardResponseDto` containing high-level KPIs, monthly performance trends, per-subject scores, and identified weak concepts — consumed by the frontend Recharts dashboard |

---

### SubjectController — `/api/subject`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `POST` | `/api/subject` | ✅ | Create a new study subject |
| `GET` | `/api/subject` | ✅ | List all subjects for the authenticated user |
| `GET` | `/api/subject/{id}` | ✅ | Get a subject by its GUID |
| `PUT` | `/api/subject/{id}` | ✅ | Update subject name or description |
| `DELETE` | `/api/subject/{id}` | ✅ | Delete a subject and cascade to its documents and KG nodes |

---

### DocumentController — `/api/document`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `POST` | `/api/document` | ✅ | Upload a document (PDF, DOCX, TXT, PPTX); enqueues a chunking job |
| `GET` | `/api/document` | ✅ | List all documents for the authenticated user |
| `GET` | `/api/document/{id}` | ✅ | Get document metadata by GUID |
| `GET` | `/api/document/{id}/download` | ✅ | Securely download or stream a document inline |
| `GET` | `/api/document/subject/{subjectId}` | ✅ | List all documents belonging to a subject |
| `PUT` | `/api/document` | ✅ | Rename or reassign a document to a different subject |
| `DELETE` | `/api/document/{id}` | ✅ | Permanently delete a document from the DB, filesystem, and KG |
| `POST` | `/api/document/{id}/retry-processing` | ✅ | Re-queue a failed chunking job for a document |

---

### ChatSessionController — `/api/chatsession`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `POST` | `/api/chatsession` | ✅ | Create a new chat session |
| `GET` | `/api/chatsession` | ✅ | Get all sessions (full chat history list) |
| `PUT` | `/api/chatsession` | ✅ | Rename a session |
| `DELETE` | `/api/chatsession/{sessionId}` | ✅ | Delete a session and all its messages |

---

### ChatMessageController — `/api/chatmessage`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `POST` | `/api/chatmessage/SendMessage` | ✅ | Send a message; AI answers using RAG over uploaded documents |
| `POST` | `/api/chatmessage/SearchWeb` | ✅ | Send a message; AI answers using a live web search |
| `GET` | `/api/chatmessage/{sessionId}` | ✅ | Get all messages within a session |
| `POST` | `/api/chatmessage/STT` | ✅ | Speech-to-Text — transcribe an uploaded audio file (`multipart/form-data`) |
| `POST` | `/api/chatmessage/{messageId}/TTS` | ✅ | Text-to-Speech — generate or retrieve cached audio for an AI message |

---

### QuizController — `/api/quiz`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `POST` | `/api/quiz/initiate` | ✅ | Initiate quiz generation or return a cached READY quiz (`200` / `202` / `409`) |
| `GET` | `/api/quiz/{quizId}/status` | ✅ | Poll the generation status (`GENERATING`, `READY`, `FAILED`) |
| `GET` | `/api/quiz/{quizId}/start` | ✅ | Start an exam attempt; returns shuffled questions with no correct-answer data |
| `POST` | `/api/quiz/{quizId}/submit` | ✅ | Submit answers and receive a score (idempotent) |
| `GET` | `/api/quiz/{quizId}/attempts` | ✅ | List all attempts by the current user for a quiz |
| `GET` | `/api/quiz/attempt/{attemptId}/review` | ✅ | Full review — correct answers, student answers, AI explanations, citations |
| `GET` | `/api/quiz/history` | ✅ | Paginated, filterable history of all quizzes the user has generated |
| `GET` | `/api/quiz/subject/{subjectId}` | ✅ | All quizzes generated for a specific subject |

---

### DocumentChunkController — `/api/documentchunk`

| Method | Path | Auth Required | Description |
|--------|------|:---:|-------------|
| `GET` | `/api/documentchunk/{documentId}` | ✅ | Inspect the vector chunks stored for a document |

---

## 🗄️ Data Models

The database is organized into multiple **PostgreSQL schemas** for domain isolation:

| Schema | Key Tables | Purpose |
|--------|------------|---------|
| `auth` | `users` | User accounts, hashed passwords, OTP fields |
| `content` | `documents`, `document_chunks`, `subjects` | Uploaded files and `vector(384)` embeddings |
| `rag` | `chat_sessions`, `chat_messages`, `chat_citations`, `chat_documents`, `chat_web_sources` | Full conversation history and RAG source tracking |
| `quiz` | `quizzes`, `quiz_questions`, `quiz_options`, `quiz_answers`, `quiz_attempts` | AI-generated quiz engine with shuffle mapping |


> **EF Core Approach:** The project uses **database-first scaffolding** via `Scaffold-DbContext`. Two manually maintained partial-class files (`AppDbContext_Partial.cs` and `DocumentChunk.Partial.cs`) register the `vector(384)` column type and the Npgsql pgvector data source — **do not overwrite or delete them** after re-scaffolding.

---

## ⚙️ Background Jobs (Hangfire)

Hangfire is used to offload long-running AI calls from the HTTP request thread, keeping API response times fast. Two job types are currently registered:

### DocumentChunkingJob

Triggered immediately after a document is uploaded:

```text
Upload Request
    │
    ▼
Save file to disk
    │
    ▼
Set document status → PENDING
    │
    ▼
Enqueue DocumentChunkingJob
    │
    ▼
Set status → PROCESSING
    │
    ▼
POST /extract/embed  →  Python AI Service
    │
    ▼
Save vector chunks to DB  (document_chunks table)
    │
    ▼
Set status → COMPLETED  (or FAILED on error)
```

### QuizGenerationJob

Triggered by `POST /api/quiz/initiate` when no cached READY quiz is found. Computes a deterministic hash from `userId + sorted documentIds` to guarantee deduplication across concurrent requests.

**Monitoring:** Navigate to `/dashboard` (Hangfire Dashboard) to monitor job queues, retry failed jobs, and inspect execution history. If a document is stuck in `FAILED`, use `POST /api/document/{id}/retry-processing` to re-enqueue.

---

## ✅ Prerequisites

Ensure the following are installed before cloning:

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8)
- [PostgreSQL 15+](https://www.postgresql.org/download/) with the **pgvector** extension enabled
- [Visual Studio 2022](https://visualstudio.microsoft.com/) or VS Code with the C# Dev Kit extension
- Git

---

## 🔧 Configuration

The project uses two configuration files that are **excluded from source control** for security. Create them manually inside `Backend/AgenticAITutor/AgenticAITutor/`.

### `appsettings.json` — Production Settings

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*",
  "ConnectionStrings": {
    "DefaultConnection": "Host=your_prod_db_host;Port=5432;Database=AgenticAITutor;Username=postgres;Password=YOUR_PROD_PASSWORD"
  },
  "AppConfig": {
    "BaseURL": "https://your-production-url.com"
  },
  "AIService": {
    "BaseURL": "http://your-ai-service-url",
    "ChunkingPath": "extract/embed",
    "ChatPath": "chat/",
    "WebSearchPath": "web-search",
    "VoicePath": "voice/ask-audio",
    "STTPath": "audio/stt",
    "TTSPath": "audio/tts",
    "KGChunkingPath": "chunk/",
    "KGDeletePath": "kg/document",
    "KGSubjectDeletePath": "kg/subject",
    "McqGeneratePath": "quiz/generate",
    "QuizChunkingPath": "quiz/process"
  },
  "JWT": {
    "Key": "REPLACE_WITH_A_VERY_LONG_SECURE_RANDOM_SECRET_KEY",
    "Issuer": "AgenticAITutor",
    "Audience": "AgenticAITutorUsers",
    "DurationInDays": 30
  },
  "EmailConfiguration": {
    "SmtpServer": "smtp.gmail.com",
    "SmtpPort": 587,
    "SenderName": "Your App Name",
    "SenderEmail": "your-app-email@gmail.com",
    "Username": "your-app-email@gmail.com",
    "Password": "your-app-specific-password"
  }
}
```

### `appsettings.Development.json` — Local Development Overrides

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=YOUR_LOCAL_PASSWORD"
  },
  "AppConfig": {
    "BaseURL": "https://localhost:7257"
  },
  "AIService": {
    "BaseURL": "http://localhost:8000",
    "ChunkingPath": "extract/embed",
    "ChatPath": "chat/",
    "WebSearchPath": "web-search",
    "STTPath": "audio/stt",
    "TTSPath": "audio/tts",
    "KGSubjectDeletePath": "kg/subject",
    "KGDocumentDeletePath": "kg/document"
  }
}
```

> **Security:** Never commit real secrets to source control. Use environment variables or a secrets manager (e.g., Azure Key Vault, AWS Secrets Manager) in production.

---

## 🚀 Installation & Setup

### Step 1 — Clone the Repository

```bash
git clone <your-repo-url>
cd Agentic-AI-Tutor/Backend/AgenticAITutor
```

### Step 2 — Set Up PostgreSQL

**Install the required extensions** (run as a PostgreSQL superuser):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**Create the database:**

```sql
CREATE DATABASE "AgenticAITutor";
```

### Step 3 — Create Configuration Files

Create `appsettings.json` and `appsettings.Development.json` as described in the [Configuration](#-configuration) section above.

### Step 4 — Scaffold the Database (EF Core Database-First)

Run the following from the **Package Manager Console** in Visual Studio:

```powershell
Scaffold-DbContext "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=YOUR_PASSWORD" `
  Npgsql.EntityFrameworkCore.PostgreSQL `
  -OutputDir Models `
  -Context AppDbContext `
  -ContextDir Data `
  -DataAnnotations -Force -NoOnConfiguring `
  -Schemas public,auth,content,planner,quiz,rag
```

Or via the `dotnet ef` CLI:

```bash
dotnet ef dbcontext scaffold \
  "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=YOUR_PASSWORD" \
  Npgsql.EntityFrameworkCore.PostgreSQL \
  --output-dir Models \
  --context AppDbContext \
  --context-dir Data \
  --data-annotations --force --no-onconfiguring \
  --schema public --schema auth --schema content --schema planner --schema quiz --schema rag
```

> ⚠️ **Important:** After scaffolding, the partial class files `AppDbContext_Partial.cs` and `DocumentChunk.Partial.cs` will **not** be overwritten — they are protected by the scaffolding configuration. Do **not** delete them.

### Step 5 — Restore NuGet Packages

```bash
dotnet restore
```

---

## ▶️ Running the Application

```bash
dotnet run
```

Or press **F5** in Visual Studio (with debugger) or **Ctrl+F5** (without debugger).

Once running, navigate to:

- **Swagger UI:** `https://localhost:7257/swagger`
- **Hangfire Dashboard:** `https://localhost:7257/dashboard`

> If the Python AI microservice is not running locally, the API will still start. Any endpoint that invokes the AI service will return a descriptive `400 Bad Request` rather than crashing.

---

## 🧩 Feature Setup Guides

### Feature 1: Authentication

1. `POST /api/auth/register` with `FirstName`, `LastName`, `Email`, `Password`, `ConfirmPassword`.
2. Copy the returned JWT token from the response body.
3. In **Swagger UI**, click **Authorize** and enter `Bearer <token>`.
4. All subsequent requests will be authenticated automatically.

> Token lifetime is controlled by `JWT.DurationInDays` in `appsettings.json` (default: 30 days).

---

### Feature 2: Document Upload & Management

1. Optionally create a subject first via `POST /api/subject`.
2. Upload a document via `POST /api/document` (multipart form-data). Supported formats: **PDF, DOCX, TXT, PPTX**.
3. The API immediately returns with `status: PENDING` and enqueues a `DocumentChunkingJob`.
4. Poll `GET /api/document/{id}` until `status` transitions to `COMPLETED` (or `FAILED`).
5. On `FAILED`, call `POST /api/document/{id}/retry-processing` to re-queue.

Files are stored under `wwwroot/uploads/{userId}/{subjectId-or-General}/`. Always access files via the `/download` endpoint — never expose the raw filesystem path to the frontend.

---

### Feature 3: RAG Chat

1. Create a session via `POST /api/chatsession`. Pass one or more `documentIds` to scope the AI's knowledge.
2. Send messages via `POST /api/chatmessage/SendMessage` with `searchWeb: false`.
3. The AI service retrieves semantically similar document chunks and returns an answer with confidence score and source citations.
4. For live web queries, use `POST /api/chatmessage/SearchWeb` with `searchWeb: true`.

> **Note:** `UserId` and `AllowedDocumentIds` are resolved server-side from the JWT token and session record. Do not send them in the request body.

---

### Feature 4: Knowledge Graph (KG)

The Python AI microservice maintains a knowledge graph derived from document content. The .NET backend is responsible for keeping the KG consistent with the database:

- **On document deletion** (`DELETE /api/document/{id}`): The backend calls `DELETE /kg/document/{id}` on the Python service to remove the document's KG nodes.
- **On subject deletion** (`DELETE /api/subject/{id}`): The backend calls `DELETE /kg/subject/{id}` to remove all KG nodes belonging to the subject.

These calls are configured via the `AIService.KGDocumentDeletePath` and `AIService.KGSubjectDeletePath` keys in `appsettings.json`.

---

### Feature 5: Quizzes

The quiz lifecycle follows a strict state machine:

```text
initiate → [GENERATING] → [READY] → start → submit → review
```

1. **Initiate:** `POST /api/quiz/initiate` with a list of `documentIds` and a `subjectId`. The server computes a hash of `userId + sorted documentIds`. If an identical READY quiz exists, it returns `200` immediately (cache hit). Otherwise it enqueues `QuizGenerationJob` and returns `202 Accepted`.
2. **Poll:** `GET /api/quiz/{quizId}/status` until the status is `READY`.
3. **Start:** `GET /api/quiz/{quizId}/start` to create an attempt. Questions and options are shuffled server-side using Fisher-Yates seeded by the `attemptId`. **No correct-answer information is returned.**
4. **Submit:** `POST /api/quiz/{quizId}/submit` with the student's selected option labels. Submission is **idempotent** — re-submitting the same `attemptId` returns the original score.
5. **Review:** `GET /api/quiz/attempt/{attemptId}/review` for the full breakdown including correct answers, the student's answers, AI-generated explanations, and source chunk citations.

---

### Feature 6: Progress & Analytics

The **Analytics** feature aggregates the authenticated user's entire quiz history into actionable, high-level insights for the frontend Recharts dashboard.

**How it works:**

1. `GET /api/Analytics/progress` is called by the frontend after a quiz attempt is submitted.
2. The `AnalyticsService` queries the `quiz` schema tables (`quizzes`, `quiz_attempts`) entirely through **EF Core LINQ** — no raw SQL.
3. The service computes and returns a `ProgressDashboardResponseDto` containing:
   - **Key KPIs** — Total quizzes taken, overall average score, best subject, and total study time estimate.
   - **Monthly Performance Trends** — Aggregated average score and quiz count grouped by calendar month (suitable for a Recharts `LineChart` or `BarChart`).
   - **Per-Subject Scores** — Average score broken down by subject (suitable for a Recharts `RadarChart` or `BarChart`).
   - **Weak Concepts** — Topics or question tags where the student's accuracy is consistently below a configurable threshold, surfaced for targeted review.

> This endpoint is designed to be called on the dashboard page load and returns a single, pre-aggregated payload — avoiding N+1 client-side fetches.

---

### Feature 7: Email (SMTP / OTP)

The forgot-password flow uses an SMTP-based email service to deliver one-time passwords:

1. `POST /api/auth/forgot-password` — The `AuthService` generates a cryptographically secure 6-digit OTP, hashes it, and stores it in the `auth.users` table alongside an expiry timestamp (15 minutes). The plain OTP is dispatched via the configured SMTP provider.
2. `POST /api/auth/reset-password` — The submitted OTP is validated against the stored hash and expiry. On success, the password is updated with BCrypt and the OTP fields are cleared.

Configure SMTP credentials in `appsettings.json` under an `Email` section (provider-specific; not shown above to avoid exposure).

> The endpoint always returns the same `200 OK` response regardless of whether the email address exists, to **prevent account enumeration attacks**.

---

### Feature 8: Hangfire Dashboard & Job Monitoring

The Hangfire Dashboard is available at `/dashboard` and provides a real-time view of:

- **Enqueued** — Jobs waiting to be picked up by a worker.
- **Processing** — Jobs currently executing.
- **Succeeded / Failed** — Completed job history with full stack traces on failure.

> ⚠️ **Security:** The Hangfire Dashboard authorization filter (`HangfireAuthorizationFilter`) currently allows all requests. **Before deploying to production**, restrict access to admin-role users only.

---

## 📖 API Documentation

Interactive API documentation is available via **Swagger UI** at `/swagger`. All endpoints include XML-doc summaries, remarks, and typed `ProducesResponseType` attributes so the generated schema is accurate and complete.

### Key NuGet Packages

| Package | Purpose |
|---------|---------|
| `Microsoft.EntityFrameworkCore` | ORM core |
| `Npgsql.EntityFrameworkCore.PostgreSQL` | PostgreSQL provider for EF Core |
| `Pgvector` / `Pgvector.EntityFrameworkCore` | `vector(384)` column type support |
| `BCrypt.Net-Next` | Password hashing |
| `Microsoft.AspNetCore.Authentication.JwtBearer` | JWT Bearer token middleware |
| `FluentValidation.AspNetCore` | Request validation rule sets |
| `SharpGrip.FluentValidation.AutoValidation.Mvc` | Automatic model validation via FluentValidation |
| `Hangfire` / `Hangfire.PostgreSql` | Background job processing with PostgreSQL storage |
| `Swashbuckle.AspNetCore` | Swagger / OpenAPI generation |
| `Microsoft.Extensions.Http.Polly` | Resilience & retry policies for `HttpClient` |

### Swagger Authorization

```
Register → Login → Copy the JWT token
    → Click "Authorize" in Swagger UI
    → Enter: Bearer <your-token-here>
```

All protected endpoints will then include the `Authorization: Bearer ...` header automatically in every Swagger request.

---

## 🔒 Security Notes

- **JWT Secret** — The `JWT.Key` in `appsettings.json` must be a long, random string. Rotate it before deploying to production. **Never commit real secrets to source control** — use environment variables or a secrets manager.
- **Hangfire Dashboard** — Currently open to all users. Restrict to admin roles before going live.
- **CORS** — Configured to `AllowAnyOrigin` for development. Lock this down to your frontend's origin domain in production.
- **File Access** — Uploaded files should always be served through `GET /api/document/{id}/download` (which validates ownership) rather than being exposed as static files directly.

---

## 📄 License

This project is for internal and educational use. Contact the project owner for licensing information.
