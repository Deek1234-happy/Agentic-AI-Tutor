# EduMind AI — Verified System Architecture Specification

## Purpose and evidence rules

This document describes the implementation in this repository, not an idealized target architecture. It is intended to be a source for a separate diagram generator and a guide to how the current application works.

- **Implemented** means there is an application path in source code.
- **Configured** means behavior depends on local environment/settings; configuration is not proof that an external service is reachable or that a configured model name is valid.
- **Partial / optional** means code exists, but it is not the default end-to-end path, requires optional dependencies/configuration, or is not exposed as a complete feature.
- **Not a live service check:** this document does not mean the application or its databases are currently running.
- Secret values are deliberately omitted. Do not put keys, passwords, SMTP credentials, or JWT signing keys in an architecture diagram.

The requested product name is **EduMind AI**. The checked-in README calls the project **GenT** and describes several broader/aspirational AI capabilities. When those descriptions differ from the actual application path, this document follows the code and flags the discrepancy below.

## 1. High-level architecture

The implemented application has three main application processes:

1. **Web client:** a React and TypeScript single-page application served by Vite.
2. **Application API:** an ASP.NET Core 8 REST API. It owns user-facing authorization, relational data, upload handling, and Hangfire background jobs.
3. **AI service:** a Python FastAPI service. It owns document parsing/embedding, chat/retrieval/LLM orchestration, quiz question generation, voice endpoints, web search, and Neo4j graph operations.

The persistent systems are PostgreSQL (including the `vector` extension), Neo4j, and local files. The browser talks to the ASP.NET API; it does **not** connect directly to PostgreSQL, Neo4j, or the Python service. The ASP.NET API calls the Python service over HTTP. The Python service accesses PostgreSQL for vector retrieval and Neo4j for graph operations. Hangfire jobs run inside the ASP.NET process and are stored in PostgreSQL.

```text
Browser → React/Vite → ASP.NET Core API → PostgreSQL
                                  ├──────→ local upload storage
                                  ├──────→ Hangfire jobs (PostgreSQL)
                                  └──────→ FastAPI AI service
                                                   ├→ PostgreSQL/pgvector
                                                   ├→ Neo4j
                                                   └→ configured external AI/search providers
```

## 2. Components and technologies

### Presentation layer

| Component | Technology and purpose | Source locations | Status / communication |
|---|---|---|---|
| Browser UI | React, TypeScript, React Router; dashboard, authentication, subjects/documents, chat, quizzes, progress, settings, and notifications | `Frontend/src/main.tsx`, `Frontend/src/app/App.tsx`, `Frontend/src/app/routes.ts`, `Frontend/src/app/pages/`, `Frontend/src/app/components/` | Implemented. Calls the ASP.NET API using HTTP(S) JSON, bearer tokens, and multipart uploads. |
| UI libraries | Vite, MUI, Radix UI, Tailwind CSS, Lucide, Recharts, React Force Graph, React Markdown | `Frontend/package.json`, `Frontend/vite.config.ts` | Used for development/build and interface elements. React Force Graph renders graph context returned by the API; it is not a browser-to-Neo4j connection. |
| API client and feature services | Fetch-based API client and service modules for auth, user, subjects, documents, chat, quiz, and analytics | `Frontend/src/lib/apiClient.ts`, `Frontend/src/services/` | Implemented. Default API URL is `http://localhost:5099`; `VITE_API_BASE_URL` can override it. Authenticated requests attach the stored JWT. |
| Browser session | `localStorage` stores the login session/token; the auth context restores it on load | `Frontend/src/context/AuthContext.tsx`, `Frontend/src/lib/apiClient.ts` | Implemented. Logout clears browser state; there is no corresponding server logout request. |
| Protected routing | React route guard redirects unauthenticated users | `Frontend/src/app/components/ProtectedRoute.tsx`, `Frontend/src/app/routes.ts` | Implemented in the UI; backend authorization remains authoritative for protected API actions. |

### Application/API layer

| Component | Technology and purpose | Source locations | Status / communication |
|---|---|---|---|
| Main REST API | ASP.NET Core 8 Web API; controllers for auth, profile, subjects, documents/chunks, chat, quiz, analytics, and a mock-AI controller | `Backend/AgenticAITutor/AgenticAITutor/Program.cs`, `Backend/AgenticAITutor/AgenticAITutor/Controllers/` | Implemented. Receives frontend requests and calls services/repositories, PostgreSQL, local storage, and the AI service. |
| Authentication and authorization | JWT bearer authentication; BCrypt password hashing; authorization attributes on protected controllers/actions | `Backend/AgenticAITutor/AgenticAITutor/Program.cs`, `Backend/AgenticAITutor/AgenticAITutor/Services/Auth/`, `Backend/AgenticAITutor/AgenticAITutor/Controllers/AuthController.cs` | Implemented. JWT is issued by the API and sent by the browser on protected API calls. |
| OTP email | Password-reset OTP and expiry are handled by the auth service; MailKit sends email using SMTP configuration | `Backend/AgenticAITutor/AgenticAITutor/Services/Auth/AuthService.cs`, `Backend/AgenticAITutor/AgenticAITutor/Services/Email/` | Implemented, configuration-dependent. Forgot-password queues email work with Hangfire; reset validates expiry and OTP. SMTP must be configured in the running environment. |
| ORM and PostgreSQL driver | Entity Framework Core, Npgsql, and Pgvector integration | `Backend/AgenticAITutor/AgenticAITutor/Data/AppDbContext.cs`, `Backend/AgenticAITutor/AgenticAITutor/Program.cs`, `.csproj` | Implemented. The API reads/writes relational records and document vectors in PostgreSQL. |
| Background jobs | Hangfire ASP.NET Core server with PostgreSQL storage and two workers | `Backend/AgenticAITutor/AgenticAITutor/Program.cs`, `Backend/AgenticAITutor/AgenticAITutor/BackgroundJobs/` | Implemented. Document processing, quiz generation, and email work are queued by the API and executed by the Hangfire server. |
| Local file storage | ASP.NET local storage service saves uploaded files under `wwwroot/uploads` and serves permitted static files/downloads | `Backend/AgenticAITutor/AgenticAITutor/Services/Storage/LocalFileStorageService.cs`, `Backend/AgenticAITutor/AgenticAITutor/Program.cs` | Implemented. PostgreSQL stores file metadata and paths; the file bytes are not stored in PostgreSQL. |
| API documentation | Swagger/Swashbuckle registration | `Backend/AgenticAITutor/AgenticAITutor/Program.cs`, `.csproj` | Available in the API configuration; not a separate runtime service. |
| Mock AI endpoints | Mock quiz-generation/process actions for test/demo behavior | `Backend/AgenticAITutor/AgenticAITutor/Controllers/MockAIController.cs` | Implemented as a mock surface; it is not the production Python AI integration. |

The API's configured development HTTP URL is `http://localhost:5099` (and HTTPS launch settings are also present). Actual binding depends on the launch profile/environment.

### API surface map

The frontend's normal API boundary is the ASP.NET API. Protected routes require a valid bearer JWT unless noted otherwise.

| Feature | ASP.NET routes |
|---|---|
| Authentication | `POST /api/Auth/register`, `/login`, `/forgot-password`, `/reset-password`; authorized `POST /api/Auth/change-password` |
| Profile | `GET`, `PUT`, `DELETE /api/User/profile` |
| Subjects | `GET`, `POST /api/Subject`; `GET`, `PUT`, `DELETE /api/Subject/{id}`; subject document dropdown route |
| Documents | `POST`, `PUT`, `GET /api/Document`; `GET /api/Document/{id}`, `/api/Document/subject/{subjectId}`, `/api/Document/{id}/download`; `DELETE /api/Document/{id}`; `POST /api/Document/{id}/retry-processing` |
| Document chunks | `GET /api/DocumentChunk/{documentId}` |
| Chat sessions | `POST`, `GET`, `PUT /api/ChatSession`; `DELETE /api/ChatSession/{sessionId}` |
| Chat messages and extra capabilities | `GET /api/ChatMessage/{sessionId}`; `POST /api/ChatMessage/SendMessage`, `/SearchWeb`, `/STT`, `/api/ChatMessage/{messageId}/TTS` |
| Quiz | `POST /api/Quiz/initiate`, `/api/Quiz/{quizId}/submit`; status/start/history/attempt/review and subject-quiz `GET` routes |
| Analytics | `GET /api/Analytics/progress` |
| Mock AI | `POST /api/mock-ai/quiz/generate`, `/api/mock-ai/quiz/process` (mock/demo surface, not the normal Python-service client) |

The FastAPI service mounts the following route groups. A mounted route is not necessarily called by the frontend or .NET API:

| AI route group | Examples | Integration status |
|---|---|---|
| Extraction | `POST /extract/`, `/extract/embed` | `/extract/embed` is called by integrated document processing; `/extract/` is separately mounted. |
| KG continuation | `POST /chunk/` | Called by the document-processing continuation to build graph data from persisted document/chunk data. |
| Search/RAG | `POST /search/`, `/rag/` | Separate retrieval routes; no normal .NET caller was found. |
| Chat | `POST /chat/` | Integrated document-grounded tutoring request. |
| Web search | `POST /web-search` | Called through the .NET chat web-search action; uses Tavily when configured. |
| Knowledge graph | `/kg/build`, `/kg/build-cross-doc`, `/kg/query/subject`, `/kg/answer/subject`, graph/document `GET` routes, graph/document `DELETE` routes | Mounted. `/chunk/` is the integrated upload path; direct graph build/query routes are separate. .NET also invokes graph deletion routes during document/subject deletion. |
| Quiz | `POST /quiz/generate`, `/quiz/process` | `/quiz/generate` is integrated with Hangfire; `/quiz/process` is a separately mounted file-processing path with no .NET caller found. |
| Voice | `POST /audio/stt`, `/audio/tts`, `/voice/ask-audio` | STT and TTS are called separately through .NET. The .NET call to `/voice/ask-audio` is commented out; it is a separate mounted route. |
| Evaluation/static | `POST /evaluate`, `/static/...` | Evaluation route and static file serving are mounted; not part of the normal learner workflow. |

FastAPI also exposes its standard interactive documentation endpoints.

### AI and processing layer

| Component | Technology and purpose | Source locations | Status / communication |
|---|---|---|---|
| AI HTTP service | Python, FastAPI, Uvicorn, Pydantic | `ai_service/app/main.py`, `ai_service/requirements.txt` | Implemented. Called by the ASP.NET API over HTTP. A common local service URL is `http://localhost:8001`; configuration can override it. |
| Document extraction and chunking | Python parsers for supported document types, text cleanup, chunk generation, and metadata/page tracking | `ai_service/app/extract.py`, `ai_service/app/chunker.py`, related parser modules | Implemented. The .NET upload endpoint currently accepts PDF, DOCX, TXT, and PPTX (up to 10 MiB); the Python parser has additional format paths that are not necessarily reachable through this upload validator. |
| Embeddings | Sentence Transformers with `intfloat/e5-base-v2`, producing 768-dimensional vectors; query/passage prefixes are supported | `ai_service/app/embedding.py`, `ai_service/app/extract.py` | Implemented. Embeddings from document processing are returned to the API for PostgreSQL storage. Query embeddings are used for vector retrieval. |
| RAG chat | FastAPI chat endpoints, conversation/history handling, query rewriting/decomposition, document-scoped retrieval, answer generation, and citation/context assembly | `ai_service/app/chat.py`, `ai_service/app/chat_service.py`, `ai_service/app/rag.py` | Implemented. The .NET chat service sends the request and persists the resulting assistant message/citations/context. |
| Vector retrieval | PostgreSQL/pgvector similarity search, scoped to the selected user/subject/documents as implemented by the retrieval request | `ai_service/app/db.py`, `ai_service/app/chat_service.py`, `ai_service/app/search.py` | Dense retrieval is used by chat. The schema has `vector(768)`; the inspected DDL does not declare an HNSW or IVFFlat index. |
| Standalone hybrid search | Dense retrieval plus Python BM25/RRF and BGE cross-encoder code in the search subsystem | `ai_service/app/search.py` and supporting retrieval modules | A separate search route/capability. Do **not** depict this as the default integrated chat pipeline unless a specific caller selects it; normal `/chat/` uses its own dense retrieval plus KG context path. |
| Knowledge graph | Neo4j driver and Python extraction/storage/query modules; nodes/edges represent user/subject/document/concept/entity relationships | `ai_service/app/kg_db.py`, `ai_service/app/kg.py`, `ai_service/app/kg_extractor.py`, `ai_service/app/kg_store.py`, `ai_service/app/kg_service.py`, `ai_service/app/chunk_kg.py` | Implemented, configuration-dependent on Neo4j. The Python service owns graph access. The frontend only receives graph context through the API. |
| Quiz generation | AI service quiz routes generate MCQ content; the API stores question/option records and evaluates submitted answers | `ai_service/app/quiz/`, `Backend/AgenticAITutor/AgenticAITutor/Services/Quiz/`, `Backend/AgenticAITutor/AgenticAITutor/BackgroundJobs/QuizGenerationJob.cs` | Implemented. Generation is an asynchronous Hangfire workflow. A local Qwen model path is conditional on local weights being present; those weights are not part of the inspected checkout. |
| LLM/provider selection | Provider/client code supports Gemini and Groq task-specific paths plus a generic OpenAI-compatible-style provider | `ai_service/app/llm.py`, `ai_service/app/kg_extractor.py`, `ai_service/app/quiz/quiz_generator.py` | Configurable. Code defaults differ by task (chat/quiz default to Gemini while KG extraction defaults to Groq); the local environment selectors set Gemini for chat/KG/quiz. The configured chat model string is `gemini-3.5-flash-lite`; quiz/KG may use task-specific configured model values. A generic LLM setting is also present. These are configuration values, not proof a model endpoint is reachable or valid. No secrets are included here. |
| External web search | Tavily client/search integration | `ai_service/app/web_search_chat.py` and related search modules | Optional/configuration-dependent. It is reached through the web-search feature path; it is not a database or local search index. |
| Speech input/output | Speech-to-text and text-to-speech routes; code includes Faster-Whisper and configurable/local speech backends | `ai_service/app/vstt.py`, `ai_service/app/vtts.py`, `ai_service/app/voice.py`, `ai_service/app/audio/` | Optional. The UI can use browser speech capabilities; server-side routes are available through the API. Local model/dependency/configuration is required for applicable backends. |
| Graph checkpoints | JSON checkpoint files support knowledge-graph processing progress/recovery | `ai_service/app/.kg_checkpoints/` | Local processing state, not a separate database or service. |
| OCR | Tesseract-related OCR support in parsing code | AI service extraction/parser modules | Optional code path; depends on local Tesseract installation/configuration and should not be represented as an always-on external OCR service. |

## 3. Data stores and database contents

### PostgreSQL and pgvector

PostgreSQL is the main relational store. The checked-in SQL DDL is `Backend/AgenticAITutor/AgenticAITutor/schema.sql`; EF entity mappings are in `Backend/AgenticAITutor/AgenticAITutor/Data/AppDbContext.cs`.

| Schema / table group | What it stores |
|---|---|
| `auth.users` | Account/profile identity, password hash, role and login metadata; password-reset OTP and expiry fields are also represented here. |
| `content.subjects` | User-owned subject/course records. |
| `content.documents` | Uploaded document metadata, ownership, processing state, hash, and stored-file path. |
| `content.document_chunks` | Extracted text chunks, page/range metadata, and 768-dimensional embeddings used for retrieval. |
| `content.quiz_chunks` | Text/metadata used as quiz-generation source material. The normal upload workflow derives these from processed document chunks with basic/default classification metadata. |
| `rag.chat_sessions`, `rag.chat_documents` | Chat session ownership/title and the documents selected for a session. |
| `rag.chat_messages`, `rag.chat_citations`, `rag.chat_web_sources` | User/assistant messages, answer context/citations, and web-search references. |
| `quiz.quizzes`, `quiz.quiz_documents` | Generated quiz metadata and associated source documents. |
| `quiz.quiz_questions`, `quiz.quiz_options` | Questions and answer options. |
| `quiz.quiz_attempts`, `quiz.quiz_answers` | User attempts, submitted answers, scores, and review data. |
| Planner, notification, and progress tables | `planner.study_plans`, related plan-item/document tables, notification preferences/notifications, and `user_topic_progress` are present in the schema. Their presence alone does not establish a complete UI/API workflow. |
| Other records | Activity logs and association/join tables are also present. Some quoted legacy join tables in `schema.sql` differ from EF's schema-qualified mappings; use the EF model and actual initialized database when verifying a running instance. |

The schema enables PostgreSQL's `uuid-ossp` and `vector` extensions. The embeddings are stored as `vector(768)`. The inspected DDL has no HNSW/IVFFlat index declaration, despite the README's HNSW claim.

At startup, the API creates required extensions/schemas and calls EF Core `EnsureCreated()`. This is not the same as applying a versioned EF migration history. The checked-in SQL file is useful for understanding the intended schema, but should not be assumed to be executed by startup unless a separate setup step does so.

### Neo4j

Neo4j is a separate graph store initialized/used by the Python AI service. The graph pipeline extracts entities/relationships from document chunks and associates graph data with user, subject, and document scope. Chat can request graph context and the API returns that context to the frontend. PostgreSQL remains the source for relational records, chat messages, and document vectors; Neo4j is not a replacement for those tables.

### Local files

- Uploaded source document bytes: local ASP.NET `wwwroot/uploads/...` storage.
- Document metadata and processing statuses: PostgreSQL.
- Optional AI-generated/static audio artifacts: AI service static/audio paths as configured by the respective voice route.
- KG progress/checkpoints: local JSON files under `ai_service/app/.kg_checkpoints/`.

These paths are local filesystem storage, not a cloud object store.

## 4. End-to-end workflows

### 4.1 Access, registration, and sign-in

1. The browser loads the React application and route configuration.
2. Registration/login forms call `POST /api/Auth/register` or `POST /api/Auth/login` on the ASP.NET API.
3. The API validates the request, hashes/checks passwords with BCrypt, and stores/loads the account in PostgreSQL.
4. On successful login, the API returns a JWT. The browser stores it in `localStorage`; the API client attaches it to later authorized calls.
5. A protected route checks for the browser session for navigation convenience. The backend independently validates the JWT and enforces authorization.
6. A 401 response clears the browser session and redirects to the public entry route.

### 4.2 Forgot password and OTP reset

1. The user submits an email address to `POST /api/Auth/forgot-password`.
2. The API creates a one-time code and expiry, records the reset data in the user's PostgreSQL record, and queues email work with Hangfire.
3. A Hangfire worker invokes the MailKit SMTP email service using configured SMTP settings.
4. The user submits the OTP and new password to `POST /api/Auth/reset-password`.
5. The API checks that the OTP matches and has not expired, updates the BCrypt password hash, and clears the reset code/expiry.

The email path depends on valid SMTP configuration in the API process. Configuration files contain credential fields; use environment-specific secret storage and never include values in architecture artifacts.

### 4.3 Subject and document upload/processing

1. The authenticated frontend creates/selects a subject through the ASP.NET subject API.
2. The frontend uploads a document as multipart form data to `POST /api/Document`, including the subject association.
3. The API checks ownership, accepted file type/size, and duplicate/hash constraints; it stores bytes locally and document metadata/status in PostgreSQL.
4. The API queues a Hangfire document-processing job.
5. The job sends the file or stored-file reference to the FastAPI extraction/embedding endpoint over HTTP.
6. The AI service parses and cleans text, chunks it, tracks source/page metadata, and generates 768-dimensional E5 embeddings.
7. The AI service returns chunk text/metadata/embeddings; the .NET service writes `content.document_chunks` and derives quiz chunks in PostgreSQL.
8. A Hangfire continuation calls the AI service chunk/KG endpoint to extract and persist graph data in Neo4j.
9. Document state is updated in PostgreSQL; the frontend polls processing status and displays the result.

**Format boundary:** the .NET upload validator accepts PDF, DOCX, TXT, and PPTX with a 10 MiB limit. Additional parsers in the Python service do not mean the normal UI upload endpoint accepts those formats.

### 4.4 Learning companion / document-grounded chat

1. The frontend creates or selects a chat session and associates selected subject documents through the ASP.NET API.
2. The user sends a question to `POST /api/ChatMessage/SendMessage` with the session/document context and JWT.
3. The API validates session/document ownership, saves the user message, and calls the configured FastAPI `/chat/` endpoint.
4. The AI service reads session/history and document scope from PostgreSQL, handles the query (including history/rewrite/decomposition where applicable), embeds the query with E5, and runs scoped dense vector retrieval against PostgreSQL/pgvector. The vector similarity threshold is configurable (default 0.5).
5. The AI service can also gather relevant Knowledge Graph context from Neo4j, then assembles an answer with source/citation/context data using the selected LLM provider. The .NET API owns chat-message writes; Python reads needed session/history/context data.
6. The API stores the assistant message, citations, and graph context in PostgreSQL and returns the response to the frontend.
7. The UI renders the answer, sources, and graph-context viewer.

In the normal integrated chat path, retrieval is dense-vector plus graph context. A separate search route contains BM25/RRF and cross-encoder functionality; do not imply every chat request uses the standalone hybrid reranker. The integrated chat confidence value is not a calibrated model score in the current path.

### 4.5 Web search

The UI's optional web-search action calls the ASP.NET chat web-search endpoint. The API forwards the request to the AI service's web-search route, which uses the configured external search provider (Tavily path) and returns web results/sources. The API can persist the response/source references as part of chat records. This is an external network dependency and distinct from PostgreSQL vector retrieval.

### 4.6 Knowledge Graph build and query

1. In the normal upload pipeline, the .NET Hangfire continuation calls the AI service's `/chunk/` route after document extraction.
2. Python chunk/KG modules extract entities and typed relationships and save them to Neo4j within the user/subject/document scope.
3. Neo4j schema/setup is initiated when the FastAPI service starts; its availability is configuration-dependent.
4. Chat queries can use graph context through the AI service, which returns relevant graph data through the .NET API.
5. The graph visualization is rendered by the browser using returned response data; the browser has no Neo4j credentials or direct Neo4j connection.

The AI service also mounts separate `/kg` build/query/get routes. The .NET API calls the AI service's KG deletion endpoints when deleting documents/subjects, but it does not connect directly to Neo4j. Standalone file-ingestion routes should not be conflated with the normal .NET upload → Hangfire → `/chunk/` continuation.

### 4.7 Quiz generation, attempt, and review

1. The frontend selects a subject and processed/eligible documents, then calls `POST /api/Quiz/initiate`.
2. The API creates quiz/job records and enqueues a Hangfire quiz-generation job.
3. The worker reads the document's quiz chunks from PostgreSQL and calls the FastAPI quiz-generation route.
4. The AI service generates MCQ content using the selected provider/model path and returns it; it does not own the application's quiz persistence.
5. The .NET worker stores questions/options in PostgreSQL and updates quiz status.
6. The frontend polls status, starts an attempt, submits answers, and requests review through the ASP.NET API.
7. The API shuffles choices as implemented, validates/submits answers, scores the attempt server-side, and stores attempt/answer records.

Local Qwen inference is conditional on local model weights being present; no such weights are included in the inspected checkout. Normal document upload copies source chunks into quiz chunks with default/limited metadata, so richer Bloom's taxonomy or multi-stage validation claims in documentation should not be assumed to describe this integrated workflow.

### 4.8 Progress and dashboard

1. The UI requests `GET /api/Analytics/progress`.
2. The API derives summaries from persisted quiz attempts and related subject/question data.
3. It returns average scores, subject summaries, monthly performance, and weak/missed-concept information for the dashboard/progress pages.

This is analytics derived from quiz data, not evidence of a trained adaptive-learning or personalization model. Study time, where surfaced, is estimated rather than directly measured. The schema includes planner/topic-progress data, but those tables do not by themselves establish an implemented planner or mastery-learning workflow.

### 4.9 Voice interaction

The chat UI supports browser speech capabilities where available and has server API paths for speech-to-text and text-to-speech. The ASP.NET API forwards STT to `/audio/stt` and TTS to `/audio/tts`; its `/voice/ask-audio` call is commented out. The mounted `/voice/ask-audio` route is a separate path. STT uses Faster-Whisper (medium model; CPU/int8 default). The TTS routes use local HybridTTS for English and Gemini TTS for supported other languages; the separate voice route uses Piper for non-Arabic and Coqui/XTTS for Arabic. These paths are optional and may require model downloads, local binaries, or provider credentials. Audio output may be served as a static/local file URL. There is no direct browser-to-AI-service connection.

### 4.10 Settings, notifications, and incomplete areas

- Profile and password change are backed by API endpoints.
- Notifications and preference controls in the current UI are hard-coded/local UI rather than a complete notifications API workflow.
- Planner, notifications, activity-log, and topic-progress tables/entities exist, but a complete user-facing backend feature was not found for each.
- A mock-AI controller is present separately from the normal AI-service integration.

## 5. Verified connections

| Source component | Destination component | Technology / protocol | Purpose |
|---|---|---|---|
| Browser React app | ASP.NET Core API | HTTP(S), JSON, bearer JWT; multipart form upload | Authentication, subjects, documents, chat, quizzes, settings, analytics, voice/web-search requests. |
| ASP.NET Core API | PostgreSQL | Npgsql / EF Core over PostgreSQL protocol | Accounts, subjects, document metadata/chunks/vectors, chat, citations, quizzes, attempts, analytics source data. |
| ASP.NET Core API | Local filesystem | .NET file I/O | Persist uploaded source files and serve downloads. |
| ASP.NET Core API | Hangfire server | In-process job enqueueing | Queue email, document processing, and quiz-generation work. |
| Hangfire server | PostgreSQL | Hangfire PostgreSQL storage | Persist and coordinate job records/state. |
| Hangfire document job | FastAPI AI service | HTTP | Extract text, chunk, embed, and continue KG processing. |
| Hangfire quiz job | FastAPI AI service | HTTP | Generate quiz question content from stored quiz chunks. |
| ASP.NET chat service | FastAPI AI service | HTTP | Send user chat, web-search, and server speech requests. |
| FastAPI AI service | PostgreSQL/pgvector | PostgreSQL protocol; vector extension | Store/read vectors and retrieve document chunks for AI requests. |
| FastAPI AI service | Neo4j | Neo4j Bolt driver/protocol | Create/query the knowledge graph and graph context. |
| ASP.NET document/subject service | FastAPI KG delete endpoints | HTTP | Delete corresponding graph data when a document/subject is deleted; .NET does not connect directly to Neo4j. |
| FastAPI AI service | Configured LLM provider | Provider SDK/API over HTTPS | Generate chat answers, extract graph entities/relations, or generate quiz items, depending on provider configuration. |
| FastAPI web-search module | Tavily (when configured) | External HTTPS API | Search the web and return source/results. |
| Hangfire email job (ASP.NET process) | SMTP server (when configured) | SMTP via MailKit | Deliver password-reset OTP emails. |
| Browser graph component | Browser-rendered response data | React Force Graph / in-memory UI data | Display graph context returned through the API; no direct database link. |

No source evidence supports a browser → PostgreSQL, browser → Neo4j, browser → FastAPI, ASP.NET → Neo4j direct, or ASP.NET → external LLM direct connection. .NET does call FastAPI for graph deletion.

## 6. Architecture diagram specification

### Actors

- Student/user in a web browser.
- SMTP service operator, LLM provider, and web-search provider are external service actors, only called when configured.

### Layers and diagram nodes

1. **Presentation layer:** Browser; React/Vite SPA; authentication context/API client; subject/document, chat, quiz, progress, settings, and notifications screens.
2. **Application layer:** ASP.NET Core 8 API; JWT/password/OTP services; subject/document/chat/quiz/analytics services; local upload storage; Hangfire workers/dashboard.
3. **AI/processing layer:** FastAPI; extraction/chunking/E5 embedding; chat/retrieval/LLM; web search; quiz generation; voice; KG extraction/query.
4. **Data layer:** PostgreSQL + pgvector; Neo4j; ASP.NET upload filesystem; AI static/audio and graph checkpoint files.
5. **External services:** SMTP; selected LLM provider; Tavily. These are configurable/optional, not all guaranteed reachable.

### Arrow direction and important data flows

- Browser → ASP.NET API: feature requests, JWT, files, question/answer/quiz interactions.
- ASP.NET API ↔ PostgreSQL: persisted account, content, processing state, chat, quiz, and analytics data.
- ASP.NET API → local upload filesystem: uploaded file bytes. The database separately stores metadata/path.
- ASP.NET API → Hangfire → PostgreSQL storage: queue and track background jobs.
- Hangfire jobs → FastAPI: document extraction/embedding/KG continuation and quiz generation.
- ASP.NET chat/voice/web services → FastAPI: chat and optional external-capability requests.
- FastAPI ↔ PostgreSQL/pgvector: chunk vectors and scoped retrieval.
- FastAPI ↔ Neo4j: graph extraction, persistence, and graph-context queries.
- FastAPI → LLM provider / Tavily: generation and optional web search.
- Hangfire email job → SMTP: password-reset OTP email.
- Response path returns through ASP.NET API → Browser; the UI renders citations, graph context, quiz state, analytics, and voice output.

### Optional, configurable, partial, and planned

| Capability | Classification | Diagram treatment |
|---|---|---|
| ASP.NET API, React UI, PostgreSQL, document processing, chat, quiz workflow | Implemented | Solid nodes and arrows. |
| Neo4j KG | Implemented but requires configured/running Neo4j | Show as a data store with a configuration/availability note. |
| LLM providers | Provider code exists; local environment selects Gemini for task providers; runtime credentials/network/model validity remain external | Show provider adapter and an optional/configurable external LLM node, not a fixed guaranteed model. |
| Tavily web search | Optional/configuration-dependent | Dashed/optional external-service node and arrow. |
| Browser/server speech | Partial/optional and backend-dependent | Dashed optional speech path. |
| Local Qwen quiz model | Conditional on weights not included in the inspected checkout | Do not depict as active; may be a note under optional model runtime. |
| Standalone BM25/RRF/BGE reranking | Separate search implementation, not the normal integrated chat retrieval path | Separate optional/standalone node; do not merge into the default chat arrows. |
| Planner, stored notifications, topic mastery | Schema/entities exist; complete UI/API workflow not verified | Label partial/data-model-only or omit from active-flow diagram. |
| Frontend notification center | UI with local/hard-coded content | Label mock/local UI, not a backend notification service. |
| OCR and alternate parser formats | Optional code paths; not proof of normal upload acceptance | Dashed/optional parser capability. |

## 7. README claims vs. verified implementation

The README describes a more extensive research/target system than the normal integrated application path. For an accurate diagram:

- The README's unified **dense + BM25 + RRF + BGE reranking** description is not the default `/chat/` path; hybrid search code is a separate route/capability. `/rag/` is also mounted as a separate retrieval path with no normal .NET caller found.
- The README's **HNSW** claim is not supported by the inspected `schema.sql`; it enables `vector` but does not declare HNSW/IVFFlat indexes.
- **Qwen2.5 fine-tuning/LoRA**, teacher-student corpus curation, and local inference should not be shown as active production flow. The application has conditional local-model code, but the model weights are absent in this checkout.
- **Groq/Gemma/Qwen model names and benchmark claims** in README are not proof those models are the active runtime selection. Provider/model selection is configurable; the local environment selects Gemini task providers.
- The README's full **Bloom-aligned multi-stage quiz validation** is not reflected in the standard upload-to-quiz-chunk path, which derives quiz chunks with limited/default metadata.
- Some supported parser/OCR/voice options are optional code paths, not services guaranteed to be installed or active.
- A schema table or frontend mock is not proof of a complete planner, notifications, or adaptive mastery backend feature.

Use the source paths and active flows in this document when generating the diagram; use README descriptions only as project context, not as implementation evidence.

## 8. Mermaid architecture flowchart

```mermaid
flowchart LR
  user[Student / user]
  browser[Web browser]

  subgraph presentation[Presentation layer]
    spa[React + TypeScript SPA<br/>Vite, React Router]
    ui[Auth, subjects, documents,<br/>chat, quiz, progress, settings]
    graphui[Graph context renderer<br/>React Force Graph]
    localSession[JWT/session in localStorage]
    spa --> ui
    ui --> graphui
    spa <--> localSession
  end

  subgraph application[Application and API layer]
    api[ASP.NET Core 8 REST API]
    auth[JWT, BCrypt, OTP services]
    subjectDoc[Subject and document services]
    chatApi[Chat, web-search and voice API]
    quizApi[Quiz and attempt services]
    analytics[Analytics service]
    jobs[Hangfire workers<br/>2 workers]
    uploads[(Local upload filesystem)]
    api --> auth
    api --> subjectDoc
    api --> chatApi
    api --> quizApi
    api --> analytics
    api --> jobs
    subjectDoc --> uploads
  end

  subgraph ai[AI and processing layer]
    fastapi[Python FastAPI AI service]
    parse[Parse, clean, chunk]
    embed[E5 embeddings<br/>768 dimensions]
    rag[Chat orchestration<br/>dense retrieval + KG context]
    hybrid[Standalone search<br/>BM25 / RRF / reranker]
    kgpipe[KG extraction and query]
    quizgen[MCQ generation]
    voice[Optional STT / TTS]
    websearch[Optional web search]
    llm[Configurable LLM provider adapter]
    fastapi --> parse --> embed
    fastapi --> rag
    fastapi --> hybrid
    fastapi --> kgpipe
    fastapi --> quizgen
    fastapi --> voice
    fastapi --> websearch
    rag --> llm
    kgpipe --> llm
    quizgen --> llm
  end

  subgraph data[Data layer]
    pg[(PostgreSQL<br/>EF Core + Hangfire storage)]
    vector[(pgvector<br/>document_chunks vector 768)]
    neo[(Neo4j graph)]
    audio[(Optional local static/audio files)]
    checkpoints[(Local KG checkpoint JSON)]
    pg --- vector
  end

  subgraph external[External services — configuration-dependent]
    smtp[SMTP server]
    llmprovider[Selected LLM API]
    tavily[Tavily web search API]
  end

  user --> browser
  browser -->|HTTP(S), JSON, JWT, multipart| api
  api <--> pg
  jobs <--> pg
  api -->|enqueue jobs| jobs
  jobs -->|HTTP: extract / embed / KG / quiz| fastapi
  chatApi -->|HTTP: chat / web / speech| fastapi
  api -->|HTTP: KG delete| fastapi
  embed -->|chunks and vectors returned| subjectDoc
  subjectDoc -->|persist chunks| pg
  rag <--> pg
  hybrid <--> pg
  kgpipe <--> neo
  kgpipe --> checkpoints
  voice --> audio
  jobs -->|OTP email via MailKit| smtp
  llm -->|HTTPS when configured| llmprovider
  voice -->|Gemini TTS when configured| llmprovider
  websearch -->|HTTPS when configured| tavily
  api -->|API response| browser
```

## 9. Ready-to-copy diagram-generator prompt

> Create a professional, readable system architecture diagram for **EduMind AI**, a source-verified learning application. Show five grouped layers: **Presentation**, **Application/API**, **AI/Processing**, **Data**, and **External Services**. The presentation layer is a React + TypeScript + Vite single-page app in the browser with authentication, subject/document management, chat, quiz, progress, settings, and a graph-context renderer. The browser calls only the ASP.NET Core 8 REST API using HTTP(S), JSON, bearer JWTs, and multipart upload; it does not connect directly to databases or the Python service.
>
> The application layer contains the ASP.NET Core API, JWT/BCrypt authentication, OTP email workflow, subject/document/chat/quiz/analytics services, local upload filesystem, and Hangfire PostgreSQL-backed background workers. Show the API reading/writing PostgreSQL using EF Core/Npgsql. Show Hangfire jobs for document processing, quiz generation, and email. Uploaded file bytes go to local filesystem storage; document metadata and chunks go to PostgreSQL.
>
> The AI layer is a Python FastAPI service called over HTTP by the ASP.NET API and Hangfire jobs. It contains document parsing/chunking, E5-base-v2 768-dimensional embeddings, document-grounded chat, quiz question generation, Knowledge Graph extraction/query, and optional web-search and speech routes. Show normal chat using PostgreSQL/pgvector dense retrieval plus Neo4j graph context before configured LLM generation. Show standalone BM25/RRF/cross-encoder search separately from the default chat path.
>
> The data layer contains PostgreSQL with schemas for auth, content, RAG chat/citations, and quizzes, including a `vector(768)` column; Neo4j for graph nodes/relationships; local upload files; and local graph-checkpoint/audio files where applicable. Hangfire uses PostgreSQL storage. The AI service connects directly to PostgreSQL for vector retrieval and to Neo4j using the Neo4j driver. The ASP.NET API does not directly connect to Neo4j.
>
> External service nodes are SMTP for password-reset OTP delivery, a configurable LLM API (local configuration selects Gemini task providers, but availability/model validity is not guaranteed), and optional Tavily web search. Use dashed arrows and “optional/configuration-dependent” labels for external providers, speech, OCR, alternate parsers, local Qwen inference, and standalone hybrid retrieval. Do not portray Qwen fine-tuning, HNSW indexes, planner/notifications, or adaptive mastery as active features: the local Qwen weights are absent, the inspected SQL has no HNSW/IVFFlat index, and planner/notification/topic-progress tables do not prove complete workflows. Label frontend notifications as local/mock UI. Include arrow directions and the data flow from browser → API → PostgreSQL/local files/Hangfire → FastAPI → PostgreSQL/Neo4j/LLM or search provider → API → browser. Do not invent services, model training pipelines, cloud file stores, or direct browser-to-database connections. Do not include credentials or secrets.

## 10. Key source entry points

- Frontend route and bootstrap: `Frontend/src/main.tsx`, `Frontend/src/app/App.tsx`, `Frontend/src/app/routes.ts`.
- Frontend API and feature services: `Frontend/src/lib/apiClient.ts`, `Frontend/src/services/`.
- API composition, auth, and Hangfire: `Backend/AgenticAITutor/AgenticAITutor/Program.cs`.
- API controllers: `Backend/AgenticAITutor/AgenticAITutor/Controllers/`.
- EF mappings and SQL DDL: `Backend/AgenticAITutor/AgenticAITutor/Data/AppDbContext.cs`, `Backend/AgenticAITutor/AgenticAITutor/schema.sql`.
- Background processing: `Backend/AgenticAITutor/AgenticAITutor/BackgroundJobs/`.
- Python FastAPI router registration: `ai_service/app/main.py`.
- Python retrieval, embeddings, and graph: `ai_service/app/chat_service.py`, `ai_service/app/search.py`, `ai_service/app/embedding.py`, `ai_service/app/kg.py`, `ai_service/app/kg_db.py`, `ai_service/app/kg_extractor.py`, `ai_service/app/kg_store.py`, `ai_service/app/kg_service.py`.
- Python quiz routes: `ai_service/app/quiz/`.
- Repository overview and its broader claims: `README.md`.
