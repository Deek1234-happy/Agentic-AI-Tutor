# EduMind AI / GenT — Complete Project Reviewer Guide

**Purpose:** a study guide for explaining the features that are present in this repository, how a user action travels through the frontend, backend, AI service and storage, and what a reviewer may ask about them.

**Evidence and limitations:** this guide was prepared from the checked-in frontend, ASP.NET Core backend, FastAPI service and SQL schema. It describes source code, not unverified product claims. It does not imply that optional providers, model weights, credentials or every feature have been tested in a live deployment. The app services were stopped when this guide was written. SQL statements are diagnostic, read-only examples for the PostgreSQL schema in `Backend\AgenticAITutor\AgenticAITutor\schema.sql`.

> **How to prepare:** learn the system overview, understand the upload → tutor → quiz → progress journey, and be candid about the implementation notes in §12. A precise explanation of what is implemented is stronger than repeating an aspirational README statement.

## 1. Project in one minute

EduMind AI is a course-centered learning web application. A learner creates an account, groups study materials into subjects, uploads documents, asks questions about selected course material, and creates practice quizzes. The platform stores the user's account, subjects, documents, conversation history, quizzes and attempts. Document text is extracted and embedded for semantic retrieval; a separate knowledge graph stores extracted educational entities and relationships. Quiz scores feed simple progress summaries.

The implementation uses three cooperating application processes:

1. **Frontend — React and Vite:** renders pages, gathers user input, handles client navigation and sends HTTP requests to the application API.
2. **Application backend — ASP.NET Core 8:** validates requests, authenticates users, enforces ownership, stores application records in PostgreSQL, saves uploaded files and schedules longer tasks.
3. **AI backend — Python FastAPI:** parses documents, creates embeddings, retrieves course content, calls configured language-model or speech providers and reads/writes AI-specific stores.

The supporting stores are:

- **PostgreSQL (+ `pgvector`):** accounts, subjects, document metadata, document chunks and vectors, chat records, quizzes, attempts and results.
- **Neo4j:** educational entities and typed graph relationships.
- **Local file storage:** original documents and generated/user audio beneath the ASP.NET app's `wwwroot\uploads` tree.
- **Hangfire, backed by PostgreSQL:** durable background work for document processing, quiz generation and reset email delivery.

### Quick spoken architecture answer

> “The React app calls our ASP.NET Core API. ASP.NET owns authentication, permissions and application data. Longer jobs run through Hangfire. For AI tasks the API calls an internal FastAPI service, which parses and retrieves study material and uses configured AI providers. PostgreSQL stores relational records and document vectors, while Neo4j stores the concept graph. The browser never connects directly to either database.”

## 2. Architecture and request flow

```text
Learner in browser
    │ React pages / hooks / API services
    │ HTTP; bearer JWT for protected calls
    ▼
ASP.NET Core 8 API
    ├── JWT + request validation + ownership checks
    ├── EF Core / Npgsql ───────────────► PostgreSQL / pgvector
    ├── local file service ─────────────► wwwroot/uploads
    ├── Hangfire workers ───────────────► PostgreSQL-backed jobs
    └── internal HTTP ──────────────────► Python FastAPI AI service
                                             ├── PostgreSQL chunk/vector reads
                                             ├── Neo4j knowledge graph
                                             └── configured LLM / search / speech
```

### What each layer is responsible for

| Layer | Plain-language responsibility | Main technologies |
|---|---|---|
| UI | Forms, routes, display, client-side feedback and request state | React 18, TypeScript, React Router 7, TanStack Query 5, Vite |
| Application API | Identity, authorization, business rules, persistence and orchestration | ASP.NET Core 8, C#, EF Core 8, Npgsql, JWT, FluentValidation |
| AI API | Parsing, chunking, embedding, retrieval, graph work, generation and speech | Python 3.11, FastAPI, Pydantic, Uvicorn, SQLAlchemy, Transformers |
| Relational store | Durable application data and vector-bearing text chunks | PostgreSQL, `uuid-ossp`, `pgvector` |
| Graph store | Nodes/edges for educational concepts and their relationships | Neo4j 5, Cypher, Bolt |
| Background work | Retryable tasks that should not hold a browser request open | Hangfire with PostgreSQL storage |
| File storage | Original uploads and produced audio | Local ASP.NET `wwwroot/uploads` directories |

Frontend styling and component dependencies include Tailwind CSS 4, Radix UI-style components, MUI, Lucide icons, Motion, Recharts, React Markdown and a graph visualization package. Exact installed packages are listed in `Frontend\package.json`.

## 3. Sign-in, account creation, and password recovery

### Registration and login

1. The public welcome page collects registration or login information.
2. Frontend `authService` sends JSON to `POST /api/Auth/register` or `POST /api/Auth/login`.
3. `AuthController` delegates to `AuthService`; `UserRepository` persists or loads the user through EF Core.
4. Registration lowercases the email, checks for an existing account and hashes the password with BCrypt. Login verifies the submitted password against the BCrypt hash.
5. On success, the backend creates a signed JWT. The frontend stores the token and a small session object in browser `localStorage` (`auth_token` and `auth_session`).
6. `apiClient` attaches `Authorization: Bearer ...` to authenticated API calls. A 401 response clears the browser session and redirects the user to the public page.
7. `ProtectedRoute` prevents a visitor without a stored session from opening the dashboard routes. The backend remains the real authorization boundary; a client-side route guard is not sufficient by itself.

**Stored in:** `auth.users` — user identity, email, BCrypt password hash, role, timestamps, and password-reset OTP/expiry fields. The browser stores a token/session, not the password hash.

**Technologies:** React, ASP.NET Core, FluentValidation, JWT bearer authentication, BCrypt, PostgreSQL.

### Forgot password and six-digit OTP

1. The user submits their email on the public forgot-password page.
2. The API generates a cryptographically random six-digit code, stores the code and a 15-minute expiry in the matching `auth.users` record, and enqueues an email task in Hangfire.
3. The HTTP response is deliberately generic whether or not an account exists. This reduces email-account enumeration, but it also means “request accepted” does **not** prove that an email was delivered.
4. A Hangfire worker calls the configured email service. SMTP is sent through MailKit using STARTTLS. Delivery depends on valid sender, SMTP host, port, username and app-password configuration, plus external mail-provider acceptance.
5. Reset submits email, OTP and new password. The service checks expiry and compares the OTP using a fixed-time comparison; on success it stores a new BCrypt hash and clears the OTP and expiry.
6. A signed-in user may instead change their password after providing the current password.

**Stored in:** `auth.users.password_reset_otp`, `otp_expiry_time`; Hangfire's persisted job/state tables; updated `password_hash`.

**Technologies:** cryptographic RNG, OTP expiry, constant-time comparison, BCrypt, Hangfire, MailKit, SMTP STARTTLS.

**Important operational note:** configure the mail settings for the environment in which the API runs. A generic success response only confirms the API returned; check Hangfire's job state and backend logs for actual SMTP failure. Never commit SMTP credentials or show them in a presentation.

### Read-only SQL: inspect an account and OTP state

Replace the placeholder with the account email in a private, authorized environment. This returns personal data: do not publish query output or include real email addresses/OTP values in a report.

```sql
SELECT id, email, created_at, last_login,
       (password_reset_otp IS NOT NULL) AS has_pending_otp,
       otp_expiry_time,
       (otp_expiry_time > CURRENT_TIMESTAMP) AS otp_is_unexpired
FROM auth.users
WHERE lower(email) = lower('<account-email>');
```

Do not select `password_hash` or `password_reset_otp` to demonstrate the workflow. To inspect the most recent reset-email jobs without printing recipients or job arguments:

```sql
SELECT j.id, j.createdat, j.statename,
       latest.name AS latest_state,
       latest.reason
FROM hangfire.job AS j
LEFT JOIN LATERAL (
    SELECT s.name, s.reason
    FROM hangfire.state AS s
    WHERE s.jobid = j.id
    ORDER BY s.createdat DESC
    LIMIT 1
) AS latest ON TRUE
WHERE j.invocationdata ->> 'Method' = 'SendPasswordResetEmailAsync'
ORDER BY j.createdat DESC
LIMIT 10;
```

Job state indicates the worker's result, not inbox placement or a human having read the message.

## 4. Profile and account settings

The Settings page reads and updates the current user's profile and offers the authenticated change-password workflow. The backend obtains the user ID from the validated token, not from a trusted browser-supplied identity. Profile reads and writes use the user repository. The profile page/API exposes profile data; password update verifies the old password before saving a new hash. Account deletion exists as a backend endpoint; database cascade rules remove owned relational data.

**Stored in:** `auth.users`; deleting a user cascades through related relational records where foreign keys specify cascade. Files and external Neo4j records are separate resources; do not assume that a PostgreSQL cascade alone removes every external file/graph object.

**Technologies:** protected API routes, JWT claims, EF Core, PostgreSQL, BCrypt.

### Read-only SQL: user-level record counts

```sql
SELECT u.id,
       (SELECT count(*) FROM content.subjects s WHERE s.user_id = u.id) AS subjects,
       (SELECT count(*) FROM content.documents d WHERE d.user_id = u.id) AS documents,
       (SELECT count(*) FROM rag.chat_sessions c WHERE c.user_id = u.id) AS chat_sessions,
       (SELECT count(*) FROM quiz.quizzes q WHERE q.user_id = u.id) AS quizzes,
       (SELECT count(*) FROM quiz.quiz_attempts a WHERE a.user_id = u.id) AS attempts
FROM auth.users u
WHERE u.id = '<user-uuid>'::uuid;
```

Use an authorized test user UUID. Avoid selecting personal content when simple counts answer the question.

## 5. Subjects and course organization

1. The Subjects page requests the current user's subjects.
2. Creating or renaming a subject sends a name to `/api/Subject`.
3. The API reads the current user ID from JWT claims; the service normalizes names and checks for duplicate names for that user.
4. The subject record is stored in `content.subjects`. Opening a subject loads its details and documents.
5. Deleting a subject goes through the backend service; its documents and associated content are handled through the service and configured relational cascades.

Subjects scope the student's material and are the organizing unit used by document upload, chat setup and quiz filtering.

**Stored in:** `content.subjects(id, name, user_id)` and its foreign-key-connected records.

**Technologies:** React Query, ASP.NET controller/service/repository, EF Core, PostgreSQL.

### Read-only SQL: subjects and their document counts

```sql
SELECT s.id, s.name, count(d.id) AS document_count
FROM content.subjects AS s
LEFT JOIN content.documents AS d ON d.subject_id = s.id
WHERE s.user_id = '<user-uuid>'::uuid
GROUP BY s.id, s.name
ORDER BY s.name;
```

## 6. Upload, process and manage study documents

### Upload path in plain terms

1. In a subject's Documents tab, the learner chooses a file. The frontend sends `multipart/form-data` to `POST /api/Document`.
2. The .NET API requires authentication and the service checks the user/subject, accepted extension and file size (10 MiB maximum). It computes a SHA-256 content hash to reject duplicate content for the same user.
3. The original file is saved beneath `Backend\AgenticAITutor\AgenticAITutor\wwwroot\uploads\<user>\<subject>\...`. PostgreSQL gets a `content.documents` row with the original name, file metadata, storage path/hash and processing statuses.
4. The API enqueues a Hangfire `DocumentChunkingJob`; it returns before the full AI processing is complete. The UI polls document status.
5. The job calls Python `POST /extract/embed` with a document URL. Python downloads the file using its guarded loader, extracts supported content, cleans it, makes semantic chunks and calculates vectors.
6. Python returns the chunk text, page ranges and vector data. It does **not** store the RAG chunks itself. The .NET service writes each chunk/vector into `content.document_chunks`.
7. The .NET processing path copies RAG text to `content.quiz_chunks`. In this integrated upload path, it assigns default quiz metadata (`understand` / `definition`, empty concepts and keywords); it does not invoke the separate richer `/quiz/process` endpoint.
8. On successful RAG/quiz preparation the job marks those statuses complete. A Hangfire continuation then calls Python `POST /chunk/` to construct the knowledge graph. RAG, quiz-chunk and KG statuses are separate lifecycle indicators.
9. If processing fails, the backend records a failed status. The UI can request `POST /api/Document/{id}/retry-processing` for retryable failure.

### Parsing, chunking and vectorization

- PDF text: PyMuPDF. Image/scanned content: optional Tesseract OCR.
- DOCX: python-docx paragraphs/tables, with image OCR paths where available.
- PPTX: python-pptx text, with image OCR paths where available.
- TXT and CSV: text/CSV readers and cleanup.
- Semantic splitting: sentence embeddings (MiniLM) help choose meaningful boundaries, rather than splitting only every fixed number of characters.
- Dense vectors: `intfloat/e5-base-v2`, 768 dimensions; PostgreSQL's `vector(768)` column stores them.
- Page ranges are retained where parser metadata allows, so the tutoring response can link evidence to source pages.

**Accepted backend upload extensions:** PDF, DOCX, TXT and PPTX. CSV is supported by AI parser code, but is not accepted by the .NET upload service. The frontend's file picker advertises some formats not accepted by the backend (for example XLSX/DOC); server validation is authoritative.

**Stored in:** original binary on disk; metadata in `content.documents`; text/page/vector in `content.document_chunks`; quiz-source text/metadata in `content.quiz_chunks`; KG entities/edges in Neo4j; KG checkpoint progress in JSON files under `ai_service\app\.kg_checkpoints`.

**Technologies:** multipart HTTP, SHA-256, Hangfire, PyMuPDF, python-docx, python-pptx, Tesseract OCR, sentence-transformers MiniLM, E5 embeddings, pgvector, PostgreSQL, Neo4j.

### Read-only SQL: document lifecycle and chunk counts

```sql
SELECT d.id, d.filename, d.file_type, d.file_size,
       d.processing_status, d.quiz_chunking_status, d.kg_status,
       d.upload_time,
       (SELECT count(*) FROM content.document_chunks c
        WHERE c.document_id = d.id) AS rag_chunks,
       (SELECT count(*) FROM content.quiz_chunks q
        WHERE q.document_id = d.id) AS quiz_chunks
FROM content.documents AS d
WHERE d.user_id = '<user-uuid>'::uuid
ORDER BY d.upload_time DESC;
```

### Read-only SQL: inspect a chunk safely

This query intentionally returns length/page metadata rather than a student's actual document text.

```sql
SELECT id, document_id, page_start, page_end,
       length(chunk_text) AS characters,
       (embedding IS NOT NULL) AS has_embedding
FROM content.document_chunks
WHERE document_id = '<document-uuid>'::uuid
ORDER BY page_start NULLS LAST, created_at;
```

## 7. Knowledge graph and concept visualization

The graph is a second representation of concepts and relationships, not a replacement for source text.

1. After RAG chunks exist, the .NET Hangfire continuation calls FastAPI `POST /chunk/`.
2. Python reads the document's persisted chunks from PostgreSQL and prepares KG-specific chunks.
3. A configured language model identifies entities/concepts and typed relationships. The extractor includes context from adjacent chunks where implemented.
4. Python writes graph structure into Neo4j: `User → Subject → Document → Entity` plus directed, semantically named relations between entities. Nodes retain user/document/subject provenance so graph retrieval can scope the results.
5. Per-document checkpoint JSON files allow KG work to resume after interruption.
6. During chat, the AI service can resolve query entities, retrieve a bounded relevant subgraph and prepare KG answer/context. The .NET API persists returned KG context with the assistant message. The React graph viewer renders that response context; the browser does not connect directly to Neo4j.

The AI API also exposes separate KG routes for graph build/query/status/list/cross-document operations and cleanup. `/kg/build` is a distinct entry path that accepts a file and independently parses it; it is not the normal upload continuation.

**Stored in:** Neo4j node/relationship properties; document processing status in `content.documents`; serialized per-message KG context in `rag.chat_messages.kg_context`; extraction checkpoints as local JSON files.

**Technologies:** Neo4j, Cypher, Bolt, Pydantic/FastAPI, configured LLM provider, JSON checkpoints, React graph visualization.

### Example Neo4j read-only graph inspection

Run in Neo4j Browser. Replace the example ID. These are read-only `MATCH`/`RETURN` queries:

```cypher
MATCH (d:Document {id: '<document-uuid>'})-[:HAS_ENTITY]->(e:Entity)
RETURN d.id, e.name, e.type
ORDER BY e.name
LIMIT 50;
```

```cypher
MATCH (d:Document {id: '<document-uuid>'})-[:HAS_ENTITY]->(a:Entity)-[r]->(b:Entity)
RETURN a.name, type(r) AS relationship, b.name
LIMIT 50;
```

## 8. Learning Companion: course-grounded chat

### Session creation and message flow

1. The student creates a chat, selects a subject and permitted documents. The frontend posts a session to `/api/ChatSession`.
2. The backend checks that the selected documents belong to the authenticated user and stores the session and its `rag.chat_documents` associations.
3. When the user sends a message, the frontend posts to `/api/ChatMessage/SendMessage`. The backend validates session ownership and derives allowed document IDs from stored session links.
4. The user message is stored, then the backend calls FastAPI `POST /chat/` with user/session/document context and language preference.
5. Python loads conversation history (up to 10 earlier messages), recognizes greeting/follow-up intent, may rewrite dependent questions, normalizes the query and may split complex questions into sub-questions. Helper-model failures generally fall back to a simpler/original query.
6. For each query, it embeds the question and searches `content.document_chunks` using pgvector cosine-distance ranking, scoped to the user and allowed documents. A configurable similarity threshold (default 0.5) filters weak matches; results are deduplicated/capped.
7. A RAG branch builds evidence context and requests an answer constrained to the selected course content. A separate KG branch obtains graph context/answer; its failure is non-fatal. The system combines the available answer branches and returns chunk/page citations and graph context.
8. The .NET service stores the assistant response, confidence field, graph JSON and citation associations; the UI renders chat history, citations and graph context.

### Retrieval terminology for a reviewer

- **RAG** means retrieve relevant source passages first, then give those passages to a generative model as answer context.
- **Dense retrieval** compares the query's embedding against stored document-chunk embeddings using vector distance. It is good at conceptual similarity even when wording differs.
- **Citation** points to retrieved chunk/page metadata. It helps the learner verify the answer; it is not a guarantee that the model interpreted the source correctly.
- **KG retrieval** finds related entities/relationships. It complements paragraph evidence but does not magically validate the generated answer.

**Important accuracy boundary:** the normal integrated `/chat/` path uses dense vector retrieval and a separate KG branch. The standalone FastAPI `/search/` path additionally implements BM25, reciprocal rank fusion (RRF) and a BGE cross-encoder reranker. Do **not** claim that every normal chat request passes through BM25/RRF/BGE reranking. Also, integrated chat's `confidence_score` is currently returned as `0.0`; do not describe it as a calibrated confidence score.

**Stored in:** `rag.chat_sessions`, `rag.chat_documents`, `rag.chat_messages`, `rag.chat_citations`; assistant `kg_context` as JSONB; audio link as applicable.

**Technologies:** React Query, ASP.NET Core, FastAPI, Python, SQLAlchemy, E5 embeddings, pgvector, Neo4j, configured chat/KG LLM providers, React Markdown, graph visualization.

### Read-only SQL: one user's chat-session metadata

```sql
SELECT s.id, s.title, s.started_at, s.updated_at,
       count(m.id) AS message_count
FROM rag.chat_sessions AS s
LEFT JOIN rag.chat_messages AS m ON m.session_id = s.id
WHERE s.user_id = '<user-uuid>'::uuid
GROUP BY s.id, s.title, s.started_at, s.updated_at
ORDER BY s.updated_at DESC;
```

### Read-only SQL: citation/page metadata without chat contents

```sql
SELECT m.id AS assistant_message_id, c.chunk_id,
       d.filename, dc.page_start, dc.page_end
FROM rag.chat_messages AS m
JOIN rag.chat_citations AS c ON c.message_id = m.id
JOIN content.document_chunks AS dc ON dc.id = c.chunk_id
JOIN content.documents AS d ON d.id = dc.document_id
WHERE m.session_id = '<session-uuid>'::uuid
  AND m.role <> 'user'
ORDER BY m.created_at, d.filename, dc.page_start;
```

## 9. Optional web search and multilingual behavior

The chat input has a web-search mode separate from course-grounded chat. It calls the protected .NET `POST /api/ChatMessage/SearchWeb` route. The backend stores the user's question, sends it to FastAPI `/web-search`, and persists the returned assistant answer and web sources. The Python path may use prior conversation to rewrite a follow-up, queries Tavily (up to five results in the inspected service), builds an answer from those results and can localize the output.

Course-material chat and web search are separate choices; do not assume that web results are included in the normal selected-document RAG pipeline.

Language choices are passed by the UI to supported AI operations. The AI code contains language instructions/localized fallback responses. Availability depends on each feature's provider and language implementation; a UI option does not imply every model produces equal quality in every language.

**Stored in:** messages in `rag.chat_messages`, source title/domain/URL in `rag.chat_web_sources`.

**Technologies:** Tavily search API, configured LLM for answer/rewrite/localization, FastAPI, .NET HTTP client.

### Read-only SQL: web sources for one session

```sql
SELECT m.id AS message_id, m.created_at,
       w.title, w.domain, w.url
FROM rag.chat_messages AS m
JOIN rag.chat_web_sources AS w ON w.message_id = m.id
WHERE m.session_id = '<session-uuid>'::uuid
ORDER BY m.created_at, w.domain;
```

## 10. Voice input and spoken answers

Voice has multiple code paths; explain which one is on the browser workflow:

- **Browser mic input:** the chat input attempts browser speech-recognition support where available and has a server transcription fallback. The normal chat message is then sent through the text-chat route.
- **Backend STT endpoint:** authenticated `POST /api/ChatMessage/STT` accepts an audio upload (maximum 10 MiB and extension validation), forwards it to FastAPI `/audio/stt`, and returns transcript text. Python uses Faster-Whisper (the inspected default is the `medium` model, CPU/int8).
- **TTS response:** authenticated `POST /api/ChatMessage/{messageId}/TTS?language=...` verifies the message/session ownership, calls FastAPI `/audio/tts` if no matching cached audio exists, saves returned WAV bytes into the user's/session's upload area and stores an audio URL on the message.
- **Full voice endpoint:** FastAPI also exposes `/voice/ask-audio` for a direct audio → transcription → chat → speech path. This is an AI API endpoint; do not imply it is the same as the frontend's regular STT/chat/TTS sequence unless the UI is confirmed to call it.

English TTS uses the configured hybrid local engine (Piper by default; code has a Coqui/XTTS path). The standalone AI TTS endpoint has a Gemini path for non-English languages. Exact behavior depends on provider configuration and model assets.

**Stored in:** original chat text in `rag.chat_messages`; generated audio file on disk; audio file URL on `rag.chat_messages.audio_url`. Transcription's temporary processing file is removed by the AI path.

**Technologies:** Web Speech API where supported, multipart uploads, Faster-Whisper, Piper/Coqui XTTS/Gemini TTS, WAV, local file storage.

### Read-only SQL: audio metadata (not audio bytes)

```sql
SELECT id, role, created_at,
       (audio_url IS NOT NULL) AS has_audio
FROM rag.chat_messages
WHERE session_id = '<session-uuid>'::uuid
ORDER BY created_at;
```

## 11. Quiz generation, attempt, review and progress

### Quiz creation

1. The UI asks for source documents/question count and sends `POST /api/Quiz/initiate`.
2. The .NET service validates ownership and checks that document and quiz-chunk processing are complete. A SHA-256 generation hash over user/documents/count supports reusing an equivalent ready quiz and handling duplicate in-progress work.
3. The API creates a quiz with a generating status, relates it to selected documents and enqueues a Hangfire generation job. The frontend polls status while generation is running.
4. The job reads `content.quiz_chunks` and calls FastAPI `POST /quiz/generate`. The Python endpoint accepts chunk text and metadata; it does not read or write the application database.
5. Python builds prompts/slots, selects candidate slots, invokes a configured quiz provider, validates generated MCQ structure and removes duplicates. A local fine-tuned Qwen model is supported only when the model files exist; they are absent from this checkout, so a configured external fallback is needed here.
6. The .NET job stores quiz questions and options in PostgreSQL and marks the quiz ready (or failed if generation fails).

**Critical implementation detail:** the normal upload job copies chunks into `content.quiz_chunks` with default `understand` / `definition` metadata and empty concept/keyword arrays. Python `/quiz/process` is a separate route that can produce richer chunk metadata; the integrated upload path does not call it. Therefore, don't claim all stored quiz content receives rich Bloom-level classification in the active workflow.

### Taking and reviewing

1. The learner opens a ready quiz. The backend creates a `quiz.quiz_attempts` record and returns options in shuffled order.
2. A server-side `shuffle_mapping` preserves the mapping from displayed labels back to stored labels. Correct answers remain server-side while the user is taking the quiz.
3. The frontend collects selections and submits them to `POST /api/Quiz/{quizId}/submit`.
4. The server checks attempt ownership, maps displayed options to originals, compares each answer with the stored correct option, stores selected/correctness rows, and records percentage and finish time. Re-submitting a completed attempt is idempotent in the inspected implementation.
5. Review shows the selected and correct answers, explanation, concept and Bloom-level metadata.

**Stored in:** `quiz.quizzes`, `quiz.quiz_documents`, `content.quiz_chunks`, `quiz.quiz_questions`, `quiz.quiz_options`, `quiz.quiz_attempts`, `quiz.quiz_answers`.

**Technologies:** Hangfire, ASP.NET Core, FastAPI/Pydantic, prompt construction, configured LLM (or optional Qwen weights), JSON HTTP responses, PostgreSQL/EF Core, server-side shuffle/scoring.

### Read-only SQL: quiz lifecycle

```sql
SELECT q.id, q.status, q.question_count, q.created_at, q.generated_at,
       count(DISTINCT qd.document_id) AS source_documents,
       count(DISTINCT qq.id) AS stored_questions
FROM quiz.quizzes AS q
LEFT JOIN quiz.quiz_documents AS qd ON qd.quiz_id = q.id
LEFT JOIN quiz.quiz_questions AS qq ON qq.quiz_id = q.id
WHERE q.user_id = '<user-uuid>'::uuid
GROUP BY q.id
ORDER BY q.created_at DESC;
```

### Read-only SQL: attempts and scores

```sql
SELECT a.id AS attempt_id, a.quiz_id, a.attempt_number,
       a.score, a.started_at, a.finished_at
FROM quiz.quiz_attempts AS a
WHERE a.user_id = '<user-uuid>'::uuid
ORDER BY a.started_at DESC;
```

### Read-only SQL: answer results for a single attempt

```sql
SELECT ans.question_id, ans.selected_option, ans.is_correct
FROM quiz.quiz_answers AS ans
JOIN quiz.quiz_attempts AS a ON a.id = ans.attempt_id
WHERE a.id = '<attempt-uuid>'::uuid
  AND a.user_id = '<user-uuid>'::uuid
ORDER BY ans.question_id;
```

## 12. Dashboard, progress, and notifications

### Dashboard and progress

The dashboard combines profile and analytics data and links to subjects, chat, quizzes and progress. The progress API aggregates **finished quiz attempts**. It reports counts, monthly averages, subject scores and weak concepts based on missed quiz concepts. “Mastery” is an average score proxy; it is not generated from a separate learner-state model. Estimated study time uses a fixed 15 minutes per attempt. The progress page does not render every field returned by the analytics DTO.

**Stored in:** primarily `quiz.quiz_attempts`, `quiz.quiz_answers`, `quiz.quiz_questions`, and quiz/subject relations. The analytics endpoint computes results from those persisted records.

**Technologies:** ASP.NET analytics controller/service/repository, EF Core aggregation, React, Recharts.

### Read-only SQL: finished attempt averages

```sql
SELECT q.subject_id,
       count(*) AS finished_attempts,
       round(avg(a.score)::numeric, 2) AS mean_score,
       max(a.finished_at) AS most_recent_finish
FROM quiz.quiz_attempts AS a
JOIN quiz.quizzes AS q ON q.id = a.quiz_id
WHERE a.user_id = '<user-uuid>'::uuid
  AND a.finished_at IS NOT NULL
GROUP BY q.subject_id
ORDER BY mean_score DESC NULLS LAST;
```

### Notifications

The `/dashboard/notifications` page currently renders hard-coded sample notification cards, unread count and switches. “Mark as Read,” “Mark All as Read,” and “Save Preferences” have no working API handlers in the inspected frontend. PostgreSQL has `notifications` and `notification_preferences` tables, but the presence of a table is not evidence of a working UI/API flow. Describe this screen as a UI prototype/mock, not a persisted notification system.

## 13. AI and engineering concepts in simple terms

| Term | Plain-language explanation in this project |
|---|---|
| RAG | Search course passages first, then ask a language model to answer with those passages as context. |
| Embedding | A model turns text into a numeric vector so semantically similar question/passages can be compared. |
| pgvector | PostgreSQL extension and vector column/operator used to store and rank embedding vectors. |
| Semantic chunking | Dividing a document into reasonably coherent passages using sentence similarity rather than arbitrary file boundaries alone. |
| BM25 | A classic keyword-based ranking algorithm. It is present in the standalone search path. |
| RRF | Combines the ranks from two retrieval lists without directly comparing their differently scaled scores. |
| Cross-encoder reranker | A more expensive model scores a question and passage together to reorder a smaller candidate set. |
| Knowledge graph | Nodes represent entities/concepts; typed directed edges represent relationships. It helps find connected concepts. |
| LLM | A configured large language model used for selected text generation, rewriting and extraction tasks. It is a provider dependency, not the database. |
| OTP | A one-time code with a limited lifetime used to authorize a password reset. |
| JWT | A signed bearer token the backend validates on protected requests. It contains claims, not a database connection. |
| Hangfire | A PostgreSQL-backed job scheduler that lets long AI/email work run outside the immediate browser request. |
| Idempotency | Repeating an operation can reuse or return the same result instead of duplicating a completed action. Used in quiz generation/submission paths. |
| OCR | Extracts text from scanned page images when the document has no usable text layer. |

## 14. Useful SQL diagnostics (read-only)

Run in `psql` connected to the app database or another PostgreSQL client. Use a test account in a private environment. All examples here are `SELECT`s; they do not update, delete or expose passwords.

### Check installed PostgreSQL extensions

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'vector')
ORDER BY extname;
```

### Check available application tables

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('auth', 'content', 'rag', 'quiz', 'planner')
  AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;
```

### Check failed/recent Hangfire job counts (no arguments)

```sql
SELECT statename, count(*) AS jobs
FROM hangfire.job
GROUP BY statename
ORDER BY statename;
```

### Check one document's chunk and embedding counts

```sql
SELECT d.id, d.filename,
       count(c.id) AS chunks,
       count(c.embedding) AS embedded_chunks
FROM content.documents AS d
LEFT JOIN content.document_chunks AS c ON c.document_id = d.id
WHERE d.id = '<document-uuid>'::uuid
GROUP BY d.id, d.filename;
```

## 15. Reviewer cross-questions and suggested answers

### Q1. What problem does the project solve?

**Answer:** It gives a learner one course-centered workflow to organize material by subject, ask questions grounded in selected study documents, inspect source citations/concept context, practice with quizzes and review scores.

### Q2. Why three application services instead of one?

**Answer:** The React client focuses on interaction; .NET centralizes identity, authorization and the existing application/domain model; Python packages AI/data-science libraries and exposes those tasks over HTTP. This separates responsibilities, though it adds deployment and service-communication complexity.

### Q3. What happens when a learner uploads a PDF?

**Answer:** .NET validates ownership/type/size and duplicate hash, saves the original and metadata, then enqueues Hangfire. A job calls FastAPI to extract, clean, semantically chunk and embed the file. The API saves returned text/page/vector rows in PostgreSQL; quiz chunks are prepared; a continuation constructs the Neo4j graph. The UI observes the processing statuses.

### Q4. Does Python save the document vectors?

**Answer:** Not on the integrated `/extract/embed` path. Python parses and returns chunks plus vectors. The .NET service persists those values in `content.document_chunks`. Python reads those rows later for retrieval.

### Q5. How does the tutor find a relevant passage?

**Answer:** It embeds the user's question and compares it with allowed chunks using pgvector distance, scoped by user and session-selected documents. A threshold drops weak matches; retrieved text is sent as context to the configured model, and the response includes chunk/page citations. The chat also has a separate KG branch.

### Q6. Is normal chat fully hybrid BM25 + vector + reranker?

**Answer:** No. The separate FastAPI `/search/` route implements dense search, BM25, RRF and a BGE reranker. The .NET app's normal chat integration calls `/chat/`, whose inspected retrieval path is dense vector search plus a separate KG branch. I would distinguish these when describing the implementation.

### Q7. What does a citation prove?

**Answer:** It identifies retrieved source chunk/page metadata so the learner can verify it. It does not prove the generated answer is correct or that the model interpreted the passage correctly.

### Q8. What exactly does the knowledge graph contain?

**Answer:** User/subject/document ownership nodes, extracted entity nodes and typed directed relationships, with provenance identifiers. PostgreSQL remains the source for document/chunk content; Neo4j stores graph topology.

### Q9. Why use PostgreSQL and Neo4j together?

**Answer:** PostgreSQL handles structured records, relationships, transactional business data and vector similarity; Neo4j is suited to traversing connected concepts and typed relationships. They are separate systems, so writes are not one distributed transaction and cleanup must be handled deliberately.

### Q10. Is the graph created synchronously during upload?

**Answer:** No. Upload returns after scheduling background work. A Hangfire continuation builds the graph after primary document processing succeeds. The UI/status endpoint should be consulted for completion.

### Q11. How does the quiz generator ensure answers are not exposed during a test?

**Answer:** The API stores correct answers and creates a server-side option shuffle mapping for the attempt. The start response sends displayed options; the submit handler maps labels back and scores on the server. The browser is not the scoring authority.

### Q12. Is the fine-tuned Qwen quiz model running here?

**Answer:** The code supports a local merged Qwen model when model files exist, but that model directory is absent in this checkout. The current quiz path therefore needs a configured remote provider fallback. I would not claim local Qwen inference is active without supplying and testing the model files.

### Q13. Are quiz chunks all classified across Bloom's Taxonomy?

**Answer:** Not in the normal integrated upload path. That path copies RAG chunks and stamps default `understand`/`definition` metadata with empty concepts/keywords. The standalone `/quiz/process` code can perform richer processing but is not called by the upload job inspected here.

### Q14. How is learner mastery calculated?

**Answer:** The current progress API calculates averages from completed quiz attempts and groups results by subject/time; “mastery” is a score-derived summary. It is not a cognitive diagnosis or a separately trained adaptive learner model.

### Q15. What does the confidence score mean?

**Answer:** In the inspected integrated chat response it is currently `0.0`, so it is not a calibrated confidence estimate and should not be presented as one.

### Q16. How are user documents isolated?

**Answer:** .NET takes the user identity from a validated JWT, checks ownership for subjects/documents/sessions, and passes user and allowed document IDs to Python retrieval. The AI service's routers do not have their own JWT layer, so it should remain a trusted internal service and must not be exposed as an unrestricted public API.

### Q17. What if a model provider or Neo4j is down?

**Answer:** Behavior is feature-specific. Chat helper-model errors may fall back to simpler query handling, KG retrieval is non-fatal to the chat branch, but generation can still fail when its required provider is unavailable. Neo4j schema initialization is non-fatal at AI-service startup. Background job status/logs should be used to identify failed document/quiz/email work; a successful HTTP acknowledgement is not proof that a queued task completed.

### Q18. How does password reset avoid revealing registered emails?

**Answer:** The API returns the same generic success message regardless of whether the email matches a user. When there is a user, it stores a short-lived OTP and enqueues SMTP delivery. Delivery is verified separately using Hangfire job state/logs; the generic HTTP response alone does not establish delivery.

### Q19. Is logout a server-side token revocation?

**Answer:** In the frontend, logout clears local token/session state and query cache. The inspected implementation does not show a server-side token blacklist/revocation store; JWT expiry and client-side removal are the normal logout behavior.

### Q20. Does the notification screen persist its controls?

**Answer:** Not currently. The UI shows sample/hard-coded notifications and preferences; its actions are not wired to an API. Tables existing in SQL do not mean the feature is implemented end-to-end.

### Q21. Is there a study-planning feature?

**Answer:** The SQL schema includes planner tables, but the inspected frontend route set and backend controllers do not expose a complete study-plan user flow. I would call it schema groundwork, not a working user-facing feature.

### Q22. What SQL migrations manage the schema?

**Answer:** The repository has a `schema.sql` snapshot. Backend startup also calls EF Core `EnsureCreated`; that creates a schema for a new database but is not an incremental migration system. Schema evolution should be managed with explicit, versioned migrations.

### Q23. Why do long operations use Hangfire?

**Answer:** Parsing large documents, calling models and generating quizzes may take longer than a normal HTTP request should remain open. Hangfire persists the work in PostgreSQL, allows a worker to process it asynchronously and exposes statuses/retries.

### Q24. What are the main limitations you would improve?

**Answer:** Align advertised features with active paths; add explicit versioned DB migrations; enrich quiz metadata in the integrated ingest flow; compute a validated confidence metric or remove the placeholder; secure/configure internal AI endpoints; implement actual notification persistence; and improve observability/error reporting for background jobs and external providers.

### Q25. What is the difference between a table/schema and a feature?

**Answer:** A table is only a storage structure. A complete feature needs a UI action, API endpoint, business logic, authorization and persistence/read behavior connected together. For example, notification tables exist, but the current notification page is static and its buttons do not call that storage.

## 16. Honest implementation boundaries to remember

These are important corrections to broad project prose:

1. The README contains outdated paths, routes and technology claims. Use actual routes and code paths as the source of truth.
2. Normal tutor chat is dense vector retrieval plus KG context, not the standalone `/search/` BM25/RRF/BGE sequence.
3. Integrated chat confidence is a zero-valued placeholder.
4. Integrated document ingestion assigns default quiz chunk metadata; the richer `/quiz/process` route is separate.
5. Local Qwen model weights are not present in this checkout; the configured quiz provider fallback is needed.
6. Notifications are sample frontend UI and are not wired to the notification database tables.
7. Planner-related SQL tables exist without a complete user-facing/API flow in the inspected routes.
8. Some Python endpoints are internal support/evaluation paths, not browser product features. The public browser workflow should go through the .NET API.
9. The checked-in SQL is a DDL snapshot, not versioned EF migrations. EF `EnsureCreated` will not reconcile every later schema change in an existing DB.
10. The app combines separate PostgreSQL, filesystem and Neo4j stores. A successful write in one does not make a cross-store operation atomic.
11. External LLM, mail, web-search and speech behavior depends on private credentials, network access, provider quota and local model availability.

## 17. Feature-to-source quick map

| Feature | Frontend | .NET API | Python / storage |
|---|---|---|---|
| Sign in/register/reset | `Frontend\src\app\pages\Welcome.tsx`, `ForgotPassword.tsx`, `ResetPassword.tsx`; `Frontend\src\services\authService.ts` | `Controllers\AuthController.cs`; `Services\Auth\AuthService.cs` | PostgreSQL `auth.users`; Hangfire + MailKit for reset |
| Profile/settings | `Frontend\src\app\pages\Settings.tsx`; `Frontend\src\services\userService.ts` | `Controllers\UserController.cs`; user service/repository | PostgreSQL `auth.users` |
| Subjects | `Frontend\src\app\pages\Subjects.tsx`, `SubjectDetail.tsx`; `Frontend\src\services\subjectService.ts` | `Controllers\SubjectController.cs`; subject service/repository | PostgreSQL `content.subjects` |
| Document upload | `Frontend\src\app\components\subject\DocumentsTab.tsx`; `Frontend\src\services\documentService.ts` | `Controllers\DocumentController.cs`; `Services\Document\DocumentService.cs`; `BackgroundJobs\DocumentChunkingJob.cs` | `ai_service\app\extract.py`, `router.py`, `parsers.py`, `chunker.py`, `embedding.py`; PostgreSQL chunks; Neo4j KG |
| Chat and citations | `Frontend\src\app\pages\Chat.tsx`, `components\chat\`; `Frontend\src\services\chatService.ts`; `hooks\useChat.ts` | `Controllers\ChatSessionController.cs`, `ChatMessageController.cs`; chat services | `ai_service\app\chat.py`, `chat_service.py`; pgvector + Neo4j |
| Web search | Chat page/input and `chatService.ts` | `ChatMessageController.cs`, `ChatMessageService.cs` | `web_search_chat.py`, `web_search_service.py`; Tavily; `rag.chat_web_sources` |
| Voice | `Frontend\src\app\components\chat\ChatInput.tsx`, message bubble | `ChatMessageController.cs`, `ChatMessageService.cs` | `vstt.py`, `vtts.py`, `audio\stt.py`, TTS modules; filesystem + audio URL |
| Quiz and review | `Frontend\src\app\pages\Quiz.tsx`, `QuizDetail.tsx`, `ActiveQuiz.tsx`, `QuizReview.tsx`; `Frontend\src\services\quizService.ts` | `Controllers\QuizController.cs`; `Services\Quiz\QuizService.cs`; `BackgroundJobs\QuizGenerationJob.cs` | `quiz_generate_router.py`, `quiz_generator.py`; PostgreSQL `quiz.*` |
| Progress | `Frontend\src\app\pages\Dashboard.tsx`, `Progress.tsx`; analytics service | `Controllers\AnalyticsController.cs`; analytics service/repository | PostgreSQL quiz attempts/answers |
| Notifications | `Frontend\src\app\pages\Notifications.tsx` | No complete wired controller flow | Hard-coded UI; do not claim persistence |

## 18. A short, strong closing explanation

> “The core value is the connected workflow: organize subject material, process it asynchronously into searchable text and concept relationships, ask source-grounded questions, practice with generated assessments, and review stored performance. The core engineering is the split between the React interface, the secured .NET application API, and the Python AI service, using PostgreSQL/pgvector for relational and semantic retrieval data and Neo4j for graph traversal. We can explain each active path separately and are explicit about prototype areas and current limitations.”

