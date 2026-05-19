# 🎓 Agentic AI Tutor — Backend API

A production-ready ASP.NET Core Web API that powers an intelligent tutoring system. It lets students upload study documents, chat with an AI tutor grounded in those documents, run web searches, generate quizzes, manage study plans, and convert audio to text and back.

---

## 📐 Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│                  ASP.NET Core Web API                  │
│  Controllers → Services → Repositories → PostgreSQL    │
│                        ↓                               │
│             Hangfire Background Jobs                   │
│                        ↓                               │
│        Python AI Microservice (external HTTP)          │
│  ┌──────────────┬──────────────┬──────────────────┐   │
│  │  /chat       │ /web-search  │  /extract/embed  │   │
│  │  /audio/stt  │ /audio/tts   │                  │   │
│  └──────────────┴──────────────┴──────────────────┘   │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | ASP.NET Core 8 Web API |
| Database | PostgreSQL 15+ with **pgvector** extension |
| ORM | Entity Framework Core (Npgsql) |
| Auth | JWT Bearer Tokens + BCrypt password hashing |
| Background Jobs | Hangfire (PostgreSQL storage) |
| Validation | FluentValidation with auto-validation |
| File Storage | Local filesystem (`wwwroot/uploads/`) |
| AI Backend | External Python microservice (HTTP) |
| API Docs | Swagger / OpenAPI with XML comments |

---

## ✅ Prerequisites

Make sure the following are installed on your machine before cloning:

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8)
- [PostgreSQL 15+](https://www.postgresql.org/download/) with the **pgvector** extension
- [Visual Studio 2022](https://visualstudio.microsoft.com/) (or VS Code with the C# Dev Kit extension)
- Git

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd AgenticAITutor
```

### 2. Set Up PostgreSQL

#### Install pgvector

The project uses `vector(384)` columns for semantic search. You must install the pgvector extension before running migrations.

```sql
-- Run this in psql or pgAdmin as a superuser
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### Create the Database

```sql
CREATE DATABASE "AgenticAITutor";
```

### 3. Initialize Configuration Files

For security reasons, `appsettings.json` and `appsettings.Development.json` are excluded from the repository. You must create them manually in the project root directory (`AgenticAITutor/AgenticAITutor/`).

**1. Create `appsettings.json` (Production Settings)**
Create a file named `appsettings.json` and add the following template. Update the JWT Key and production database string when deploying:
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
    "STTPath": "audio/stt",
    "TTSPath": "audio/tts",
    "KGSubjectDeletePath": "kg/subject",
    "KGDocumentDeletePath": "kg/document"
  },
  "JWT": {
    "Key": "REPLACE_WITH_A_VERY_LONG_SECURE_RANDOM_SECRET_KEY",
    "Issuer": "AgenticAITutor",
    "Audience": "AgenticAITutorUsers",
    "DurationInDays": 30
  }
}
```

**2. Create `appsettings.Development.json` (Local Development Settings)**
Create a file named `appsettings.Development.json`. This overrides the `appsettings.json` during local development:
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

### 4. Apply Database Migrations / Scaffold

The project uses **EF Core with database-first scaffolding**. To re-scaffold from your local database schema, run this command in the **Package Manager Console** (or `dotnet ef` CLI):

```powershell
# Package Manager Console (Visual Studio)
Scaffold-DbContext "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=YOUR_PASSWORD" `
  Npgsql.EntityFrameworkCore.PostgreSQL `
  -OutputDir Models `
  -Context AppDbContext `
  -ContextDir Data `
  -DataAnnotations -Force -NoOnConfiguring `
  -Schemas public,auth,content,planner,quiz,rag
```

```bash
# dotnet CLI equivalent
dotnet ef dbcontext scaffold \
  "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=YOUR_PASSWORD" \
  Npgsql.EntityFrameworkCore.PostgreSQL \
  --output-dir Models \
  --context AppDbContext \
  --context-dir Data \
  --data-annotations --force --no-onconfiguring \
  --schema public --schema auth --schema content --schema planner --schema quiz --schema rag
```

> ⚠️ **Important:** After scaffolding, the two partial class files (`AppDbContext_Partial.cs` and `DocumentChunk.Partial.cs`) will **not** be overwritten. They register the `vector(384)` column type and the pgvector data source configuration — do not delete them.

### 5. Install NuGet Packages

If packages are not restored automatically, run:

```bash
dotnet restore
```

Key packages the project depends on:

```text
Microsoft.EntityFrameworkCore
Npgsql.EntityFrameworkCore.PostgreSQL
Pgvector
Pgvector.EntityFrameworkCore
BCrypt.Net-Next
Microsoft.AspNetCore.Authentication.JwtBearer
FluentValidation.AspNetCore
SharpGrip.FluentValidation.AutoValidation.Mvc
Hangfire
Hangfire.PostgreSql
Swashbuckle.AspNetCore
Microsoft.Extensions.Http.Polly
```

### 6. Configure the AI Service URL

The .NET API talks to a Python AI microservice for document chunking, chat, web search, STT, and TTS. Ensure the base URL in `appsettings.Development.json` correctly points to your local Python service (default: `http://localhost:8000`).

If the Python service is not running locally yet, the API will still start. Any endpoint that calls the AI service will return a `400` error with a descriptive message rather than crashing.

### 7. Run the Application

```bash
dotnet run
```

Or press **F5** in Visual Studio (with debugging) or **Ctrl+F5** (without debugging).

> ⚠️ **Known Issue with VS Debugger + File Uploads:** If the application crashes when uploading a file with the debugger attached, see the [Known Issues](#-known-issues) section below.

Once running, navigate to:

- **Swagger UI:** `https://localhost:7257/swagger`
- **Hangfire Dashboard:** `https://localhost:7257/dashboard`

---

## 🗂️ Project Structure

```text
AgenticAITutor/
│
├── Controllers/            # HTTP endpoints (Auth, Chat, Documents, Subjects, User)
├── Services/               # Business logic layer
├── Repositories/           # Data access layer (EF Core)
├── Models/
│   ├── (entity classes)    # EF Core database models
│   └── DTOs/               # Request/Response objects
├── BackgroundJobs/         # Hangfire job definitions (DocumentChunkingJob)
├── Data/                   # AppDbContext + partial for vector config
├── Validators/             # FluentValidation rules
├── Extensions/             # ClaimsPrincipal helpers (GetUserId)
├── Filters/                # Hangfire dashboard auth filter
├── Helpers/                # JWT config class
├── wwwroot/
│   └── uploads/            # Uploaded files stored here (gitignored)
├── appsettings.json        # Production config (do not commit secrets)
├── appsettings.Development.json  # Local dev config
└── Program.cs              # DI registrations & middleware pipeline
```

---

## 🔑 Authentication

All endpoints except `POST /api/auth/register` and `POST /api/auth/login` require a **JWT Bearer token**.

**Register → Login → Copy the token → Click "Authorize" in Swagger → Paste `Bearer <token>`**

Token lifetime is configured in `appsettings.json` under `JWT.DurationInDays` (default: 30 days).

---

## 📡 API Endpoints at a Glance

| Group | Method | Path | Description |
|---|---|---|---|
| Auth | POST | `/api/auth/register` | Register a new user |
| Auth | POST | `/api/auth/login` | Login and receive a JWT |
| User | GET | `/api/user/profile` | Get current user profile |
| User | PUT | `/api/user/profile` | Update profile |
| User | DELETE | `/api/user/profile` | Delete account |
| Subject | POST | `/api/subject` | Create a study subject |
| Subject | GET | `/api/subject` | List all subjects |
| Subject | GET | `/api/subject/{id}` | Get subject by ID |
| Subject | PUT | `/api/subject/{id}` | Update subject |
| Subject | DELETE | `/api/subject/{id}` | Delete subject |
| Document | POST | `/api/document` | Upload a document (PDF, DOCX, TXT, PPTX) |
| Document | GET | `/api/document` | List all documents |
| Document | GET | `/api/document/{id}` | Get document by ID |
| Document | GET | `/api/document/{id}/download` | Securely download or view a document inline |
| Document | GET | `/api/document/subject/{subjectId}` | Documents by subject |
| Document | PUT | `/api/document` | Rename or move document |
| Document | DELETE | `/api/document/{id}` | Permanently delete document (DB, Files, & KG) |
| Document | POST | `/api/document/{id}/retry-processing` | Retry a failed chunking job |
| Chat Session | POST | `/api/chatsession` | Create a chat session |
| Chat Session | GET | `/api/chatsession` | Get all sessions (chat history) |
| Chat Session | PUT | `/api/chatsession` | Rename a session |
| Chat Session | DELETE | `/api/chatsession/{sessionId}` | Delete a session |
| Chat Message | POST | `/api/chatmessage/SendMessage` | Send message → AI answers from documents |
| Chat Message | POST | `/api/chatmessage/SearchWeb` | Send message → AI answers from the web |
| Chat Message | GET | `/api/chatmessage/{sessionId}` | Get all messages in a session |
| Chat Message | POST | `/api/chatmessage/STT` | Speech-to-Text (audio file → transcript) |
| Chat Message | POST | `/api/chatmessage/{messageId}/TTS` | Text-to-Speech (AI message → audio URL) |
| Chunks | GET | `/api/documentchunk/{documentId}` | Get chunks for a document |

---

## 🗄️ Database Schemas

The database is organized into multiple PostgreSQL schemas:

| Schema | Tables | Purpose |
|---|---|---|
| `auth` | `users` | User accounts |
| `content` | `documents`, `document_chunks`, `subjects` | Uploaded files and vector embeddings |
| `rag` | `chat_sessions`, `chat_messages`, `chat_citations`, `chat_documents`, `chat_web_sources` | Conversation history |
| `quiz` | `quizzes`, `quiz_questions`, `quiz_options`, `quiz_answers`, `quiz_attempts` | Quiz engine |
| `planner` | `study_plans`, `study_plan_items`, `study_plan_documents` | Study scheduling |
| `public` | `activity_logs`, `notifications`, `notification_preferences`, `user_topic_progress` | Misc / analytics |

---

## ⚙️ Background Jobs (Hangfire)

When a document is uploaded, it is immediately saved to disk and a **Hangfire background job** is enqueued to process it asynchronously:

```text
Upload → Save file → Set status PENDING → Enqueue DocumentChunkingJob
                                                    ↓
                                         Set status PROCESSING
                                                    ↓
                                    POST to Python /extract/embed
                                                    ↓
                                    Save vector chunks to DB
                                                    ↓
                                         Set status COMPLETED
                                         (or FAILED on error)
```

Monitor jobs at `/dashboard`. If a document gets stuck in `FAILED`, use the **retry-processing** endpoint to re-queue it.

---

## 📁 File Storage

Uploaded files are stored under `wwwroot/uploads/` following this structure:

```text
wwwroot/
└── uploads/
    └── {userId}/
        ├── General/          ← Documents with no subject
        └── {subjectId}/      ← Documents assigned to a subject
```

The `StoragePath` stored in the database is the **relative path only** (e.g., `uploads/abc-123/General/file.pdf`). To access files securely, the frontend should use the `/api/document/{id}/download` endpoint with the JWT Bearer token.

---

## ⚠️ Known Issues

### Fatal Crash on File Upload with VS Debugger Attached

**Symptom:** Swagger shows "Failed to fetch" when uploading a file. The debugger detaches. No breakpoint in the controller is hit.

**Cause:** `HttpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true")` is called inside service methods on every request. Because `HttpClient` is registered as a singleton-scoped-per-factory but services are scoped, concurrent requests from Hangfire workers and Kestrel I/O threads both mutate the same non-thread-safe `DefaultRequestHeaders` dictionary simultaneously. Under debugger load (which increases thread pool pressure), this race condition corrupts native memory and kills the process.

**Fix:** Register named HTTP clients with the header pre-configured at startup in `Program.cs`, and inject `IHttpClientFactory` instead of `HttpClient` directly:

```csharp
// Program.cs
builder.Services.AddHttpClient(nameof(ChatMessageService), client =>
{
    client.Timeout = TimeSpan.FromMinutes(10);
    client.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
});

builder.Services.AddHttpClient(nameof(DocumentChunkService), client =>
{
    client.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
});
```

```csharp
// In ChatMessageService and DocumentChunkService constructors
public ChatMessageService(IHttpClientFactory httpClientFactory, ...)
{
    this.httpClient = httpClientFactory.CreateClient(nameof(ChatMessageService));
    // Remove: this.httpClient.Timeout = TimeSpan.FromMinutes(10); ← now in Program.cs
}
```

Then remove **all** `httpClient.DefaultRequestHeaders.Add(...)` calls from inside service methods.

---

## 🔒 Security Notes

- **Hangfire Dashboard** at `/dashboard` is currently open to everyone (`HangfireAuthorizationFilter` always returns `true`). Before deploying, restrict it to admin users.
- **JWT Secret** in `appsettings.json` must be rotated before going to production. Never commit real secrets to source control — use environment variables or a secrets manager.
- **CORS** is configured to `AllowAnyOrigin` for development. Lock this down to your frontend domain in production.

---

## 🤝 Contributing

1. Create a feature branch from `main`: `git checkout -b feature/your-feature-name`
2. Make your changes and ensure the project builds: `dotnet build`
3. Open a Pull Request with a clear description of what was changed and why.

---

## 📄 License

This project is for internal/educational use. Contact the project owner for licensing information.
