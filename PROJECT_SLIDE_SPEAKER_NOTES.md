# Speaker Notes and Technical Guide for the Presentation

This guide follows the **same order as the 10 slides/screenshots provided**. For each slide:

1. Use **Speaker notes (simple)** as a short script to say aloud.
2. Use **Technical working** to understand and answer questions about what the code does.
3. Use **Code locations** to find the implementation in the repository.

The technical explanations describe the implementation in this checkout. They avoid claiming that features are wired where they are not.

---

## Slide 1 — User Interface

### Speaker notes (simple)

“This is the main interface of EduMind AI. A new user can register or log in from the landing page. After signing in, the user enters a workspace with sections for Dashboard, Subjects, Learning Companion, Quizzes, Progress, and Settings. The navigation keeps the study activities together.”

### Technical working

- The frontend is a React and TypeScript single-page application built with Vite.
- React Router selects which page to display for a URL. Public routes include the landing page, forgot password, and reset password. Dashboard and learning routes are protected by `ProtectedRoute`.
- After sign-in, the shared `MainLayout` displays the navigation and the selected page.
- Frontend service modules send HTTP requests to the ASP.NET Core API. Protected requests include the signed-in user's JWT. The browser does not connect directly to PostgreSQL or Neo4j.
- Components use the project's UI libraries and CSS styling for forms, dialogs, icons, notifications, and loading states.

### Code locations

- `Frontend/src/app/routes.ts` — public and protected route map.
- `Frontend/src/app/components/ProtectedRoute.tsx` — frontend route guard.
- `Frontend/src/app/layouts/MainLayout.tsx` — shared application navigation/layout.
- `Frontend/src/lib/apiClient.ts` — API base URL, bearer token, HTTP errors.
- `Frontend/package.json` — frontend dependencies.

---

## Slide 2 — Register / Login

### Speaker notes (simple)

“A new user registers with a name, email, and password. The password must meet the application's requirements, and the form asks the user to confirm it. Existing users sign in with their email and password. After a successful registration or login, they are taken to the dashboard.”

### Technical working

1. The registration/login modal on the welcome page collects the fields and checks that required values are present. The frontend checks that the two registration passwords match.
2. The frontend calls `POST /api/Auth/register` or `POST /api/Auth/login`.
3. ASP.NET Core `AuthController` passes the request to `AuthService`, which checks for a duplicate email or verifies the password against the saved hash.
4. `BCryptPasswordHasher` hashes passwords before storage and verifies submitted passwords during login. The plain-text password is not stored in the user table.
5. On success, the API returns a JWT. The frontend stores the token/session in browser local storage and uses the token for later protected requests.
6. The backend validates the JWT and determines the caller's user ID from its claims for protected actions. The frontend's route guard alone is not the security boundary.

**Technologies:** React, TypeScript, ASP.NET Core, FluentValidation, BCrypt, JWT bearer authentication, EF Core, PostgreSQL.

### Code locations

- `Frontend/src/app/pages/Welcome.tsx` — login/register UI and submit handlers.
- `Frontend/src/services/authService.ts` — calls the auth API and persists session.
- `Frontend/src/types/auth.ts` — request and response shapes.
- `Frontend/src/context/AuthContext.tsx` — browser session state.
- `Frontend/src/lib/apiClient.ts` — token attachment and 401 handling.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/AuthController.cs` — register/login endpoints.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Auth/AuthService.cs` — account checks, password verification and token creation.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Auth/BCryptPasswordHasher.cs` — password hashing.
- `Backend/AgenticAITutor/AgenticAITutor/Validators/RegisterRequestValidator.cs` — server-side registration rules.

---

## Slide 3 — OTP / Reset Password

### Speaker notes (simple)

“If a user forgets their password, they enter their account email. The system creates a six-digit reset code and requests that it be sent by email. The code expires after 15 minutes. The user enters the code and chooses a new password. If the code is valid, the password is reset.”

### Technical working

1. The forgot-password page calls `POST /api/Auth/forgot-password` with the email.
2. ASP.NET `AuthService` finds the account, generates a cryptographically random six-digit OTP, saves the OTP and 15-minute expiry on the user record, then queues an email job in Hangfire.
3. A Hangfire worker calls the registered email service. `SmtpEmailService` uses MailKit and SMTP STARTTLS to send the message. Email delivery requires valid SMTP settings and provider acceptance.
4. The API returns a generic message whether or not the email is registered. This reduces account enumeration; it also means the generic success response by itself does not prove delivery.
5. The reset page calls `POST /api/Auth/reset-password` with the email, OTP, and new password. The backend checks the expiry and OTP, saves the new BCrypt password hash, and clears the OTP fields.

**Technologies:** React, ASP.NET Core, cryptographic random number generation, Hangfire, MailKit, SMTP STARTTLS, PostgreSQL, BCrypt.

### Code locations

- `Frontend/src/app/pages/ForgotPassword.tsx` — email request form.
- `Frontend/src/app/pages/ResetPassword.tsx` — code and new-password forms.
- `Frontend/src/services/authService.ts` — forgot/reset API calls.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/AuthController.cs` — reset endpoints.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Auth/AuthService.cs` — OTP creation, expiry, verification and password update.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Email/SmtpEmailService.cs` — SMTP message delivery.
- `Backend/AgenticAITutor/AgenticAITutor/Program.cs` — Hangfire and email-service registration.
- `Backend/AgenticAITutor/AgenticAITutor/schema.sql` — OTP and expiry columns on `auth.users`.

---

## Slide 4 — Dashboard

### Speaker notes (simple)

“The dashboard gives the learner a quick overview of account and study activity. It shows the number of subjects, uploaded files, and quizzes taken. It also shows progress by subject and provides shortcuts to the main study features.”

### Technical working

- The dashboard loads the signed-in user's profile, including subject, document, and quiz counts.
- Separately, it requests the progress API to display a summary for each subject.
- ASP.NET calculates analytics from stored user and quiz data; React displays the returned values in cards and progress bars.
- Loading skeletons are shown while requests are in progress. If the progress request fails, the UI shows an error notification and an empty state.
- The displayed subject mastery is based on quiz scores in this implementation. It is not a separately trained learner-model prediction.

**Technologies:** React, TypeScript, ASP.NET Core, EF Core, PostgreSQL, progress-bar UI components.

### Code locations

- `Frontend/src/app/pages/Dashboard.tsx` — dashboard cards, summary and shortcuts.
- `Frontend/src/hooks/useUserProfile.ts` — profile data request.
- `Frontend/src/services/userService.ts` — profile API.
- `Frontend/src/services/analyticsService.ts` — progress API.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/UserController.cs` — profile endpoint.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/AnalyticsController.cs` — progress endpoint.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Analytics/AnalyticsService.cs` — analytics calculations.

---

## Slide 5 — Subjects

### Speaker notes (simple)

“The student creates a separate subject for each course—for example, Database Management, PHP, Artificial Intelligence, or Computer Networks. After creating a subject, the student can open it and manage the study documents for that course. This keeps each course's material organized.”

### Technical working

1. The Subjects page loads the current user's subjects from `GET /api/Subject`.
2. Creating a subject sends its name to `POST /api/Subject`. Rename and delete actions use the matching update/delete endpoints.
3. The ASP.NET API identifies the user from the JWT. The subject service stores the subject with that user ID and restricts subject reads/updates to the owner.
4. EF Core stores subject records in PostgreSQL, in `content.subjects`.
5. Once created, selecting a subject opens its subject-detail page, which loads that subject's documents.

**Technologies:** React, TanStack Query, ASP.NET Core controller/service/repository, EF Core, PostgreSQL.

### Code locations

- `Frontend/src/app/pages/Subjects.tsx` — subject list, create, rename and delete UI.
- `Frontend/src/app/pages/SubjectDetail.tsx` — selected subject page.
- `Frontend/src/hooks/useSubjects.ts` — subject queries.
- `Frontend/src/services/subjectService.ts` — frontend API requests.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/SubjectController.cs` — subject endpoints.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Subject/SubjectService.cs` — subject ownership and business rules.
- `Backend/AgenticAITutor/AgenticAITutor/Repositories/Subject/SubjectRepository.cs` — database operations.
- `Backend/AgenticAITutor/AgenticAITutor/schema.sql` — `content.subjects`.

---

## Slide 6 — Subjects: Documents

### Speaker notes (simple)

“Inside a subject, the student uploads the related course materials. For example, PHP notes are uploaded to the PHP subject. The document first appears as queued or processing. Once processing is complete, it can be selected for Learning Companion chats and quiz generation. The student can also view, download, delete, or retry processing for a failed document.”

### Technical working

1. The Documents tab submits the file as multipart form data to the ASP.NET document API.
2. The backend checks the authenticated user and subject, allowed file type and size, and computes a SHA-256 hash to detect duplicate content.
3. The original file is saved under the backend's `wwwroot/uploads` directory. Metadata and processing statuses are stored in `content.documents`.
4. The backend enqueues a Hangfire job rather than processing the file during the upload request.
5. The job asks the Python FastAPI service to extract and embed the document. Python returns the processed chunks; the .NET service stores text, page ranges and vectors in `content.document_chunks`.
6. The normal document pipeline copies those chunks to `content.quiz_chunks` with default metadata for quiz generation.
7. After the main chunking succeeds, a Hangfire continuation requests knowledge-graph processing. RAG, quiz-chunk and KG status fields indicate the separate processing stages.
8. The Documents tab polls while processing is pending, then reflects completion or failure. Retry calls the backend retry endpoint.

**Accepted file formats in the backend:** PDF, DOCX, TXT, PPTX. **Maximum:** 10 MiB per file. The server's validation is authoritative even if a browser file picker suggests additional extensions.

**Technologies:** React, multipart HTTP, ASP.NET Core, SHA-256, Hangfire, Python FastAPI, PyMuPDF, python-docx, python-pptx, sentence-transformers, E5 embeddings, PostgreSQL/pgvector, Neo4j, local file storage.

### Code locations

- `Frontend/src/app/components/subject/DocumentsTab.tsx` — upload, status, view, download, delete and retry UI.
- `Frontend/src/hooks/useSubjectDocuments.ts` — document list and processing refresh.
- `Frontend/src/services/documentService.ts` — document API requests.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/DocumentController.cs` — authenticated document routes.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Document/DocumentService.cs` — validation, hashing, file storage and job scheduling.
- `Backend/AgenticAITutor/AgenticAITutor/BackgroundJobs/DocumentChunkingJob.cs` — processing status and background pipeline.
- `Backend/AgenticAITutor/AgenticAITutor/Services/DocumentChunk/DocumentChunkService.cs` — AI request and persistence of chunks/vectors.
- `ai_service/app/main.py` — registers the FastAPI routers.
- `ai_service/app/extract.py`, `router.py`, `parsers.py`, `chunker.py`, `embedding.py` — extraction, cleanup, chunking and embeddings.
- `Backend/AgenticAITutor/AgenticAITutor/schema.sql` — `content.documents`, `content.document_chunks`, and `content.quiz_chunks`.

---

## Slide 7 — Learning Companion: Start Chat and Ask a Question

### Speaker notes (simple)

“To start a Learning Companion chat, the student chooses a subject and then selects the processed documents to use as study material. The student asks a question in the chat. The system searches the selected documents for relevant content and uses it to help prepare an answer.”

### Technical working

1. `NewChatModal` loads the user's subjects. When a subject is chosen, it loads that subject's documents.
2. The modal only offers documents whose RAG processing and knowledge-graph statuses are `COMPLETED`. It requires at least one selected document.
3. The frontend calls `POST /api/ChatSession` with the selected document IDs.
4. The .NET backend checks ownership and persists the session and the session/document links in `rag.chat_sessions` and `rag.chat_documents`.
5. Sending a normal question calls `POST /api/ChatMessage/SendMessage`. The backend validates the session, stores the user message, and calls the Python chat endpoint.
6. Python uses conversation history for follow-ups, embeds the question, and retrieves matching chunks from PostgreSQL/pgvector using the user and allowed document IDs. Retrieved text is passed to the configured language model as context. A knowledge-graph branch may supply additional related-concept context.
7. The ASP.NET backend stores the assistant response and citations; the frontend displays the conversation.

**Important accuracy note:** the integrated chat path uses dense vector retrieval plus a separate graph branch. The separate `/search/` route implements BM25, reciprocal-rank fusion and cross-encoder reranking; do not imply all of those stages run for each normal chat message.

**Technologies:** React, TanStack Query, ASP.NET Core, FastAPI, Python, E5 embeddings, pgvector, PostgreSQL, Neo4j, configured LLM provider.

### Code locations

- `Frontend/src/app/pages/Chat.tsx` — chat page and active session.
- `Frontend/src/app/components/chat/NewChatModal.tsx` — subject/document selection.
- `Frontend/src/app/components/chat/ChatInput.tsx` — question, language and web-search input controls.
- `Frontend/src/hooks/useChat.ts` — chat session and message requests.
- `Frontend/src/services/chatService.ts` — chat API calls.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/ChatSessionController.cs` and `ChatMessageController.cs` — session/message endpoints.
- `Backend/AgenticAITutor/AgenticAITutor/Services/ChatSession/ChatSessionService.cs` — session ownership and document links.
- `Backend/AgenticAITutor/AgenticAITutor/Services/ChatMessage/ChatMessageService.cs` — request orchestration and persistence.
- `ai_service/app/chat.py` and `chat_service.py` — Python chat route and retrieval/answer flow.
- `ai_service/app/vector_store.py` and `embedding.py` — pgvector retrieval and text embeddings.

---

## Slide 8 — Learning Companion: Answers, Sources, Web Search and Languages

### Speaker notes (simple)

“The Learning Companion shows the answer in the chat. When document sources are available, the student can open them and see the source document and page details. The student can choose web search when the question needs information from the web. The interface also provides language choices, microphone input, and a listen option where supported. If graph context is returned, the student can open it from the response.”

### Technical working

**Document-based answers and sources**

- For ordinary chat, Python returns an answer with citations tied to retrieved document chunks and available page ranges.
- .NET stores citations in `rag.chat_citations`; the UI's message bubble renders the sources and may request document metadata to show a filename.
- The answer text is rendered as Markdown. Returned graph context can open the Knowledge Graph viewer.
- Citations help the student verify the evidence; they do not guarantee the generated answer is correct.

**Separate web-search mode**

- The web-search switch changes the frontend request to `POST /api/ChatMessage/SearchWeb`; this is separate from the normal document-grounded message endpoint.
- The .NET service calls the Python web-search route, which uses the configured Tavily integration and returns an answer and source metadata.
- The backend stores web source records separately in `rag.chat_web_sources`.

**Language and audio**

- The frontend offers English, Kannada, Hindi, Malayalam, Tamil and Telugu as chat language choices.
- Microphone input uses browser speech recognition where available, with a server-transcription fallback using the backend STT endpoint.
- The Listen control uses browser speech synthesis when available and can use the server TTS endpoint in supported cases. Audio may be cached on the backend.
- Availability and voice quality depend on browser support, installed/local models and configured external providers.

**Technologies:** React Markdown, React, ASP.NET Core, FastAPI, Tavily, configured LLM, Web Speech APIs, Faster-Whisper, Piper/Coqui/Gemini TTS paths, PostgreSQL, local audio files.

### Code locations

- `Frontend/src/app/components/chat/MessageBubble.tsx` — answer rendering, citations, graph button and Listen action.
- `Frontend/src/app/components/chat/ChatInput.tsx` — web-search switch, language selector and microphone input.
- `Frontend/src/types/language.ts` — language options.
- `Frontend/src/hooks/useChat.ts` and `services/chatService.ts` — chat, web search, STT and TTS requests.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/ChatMessageController.cs` — normal chat, web-search, STT and TTS API routes.
- `Backend/AgenticAITutor/AgenticAITutor/Services/ChatMessage/ChatMessageService.cs` — AI service calls and stored results.
- `ai_service/app/web_search_chat.py` and `web_search_service.py` — Python web-search answer/source flow.
- `ai_service/app/vstt.py`, `audio/stt.py`, `vtts.py`, `audio/hybrid_tts.py` — speech routes/engines.
- `Backend/AgenticAITutor/AgenticAITutor/schema.sql` — `rag.chat_citations`, `rag.chat_web_sources`, and chat-message audio metadata.

---

## Slide 9 — Knowledge Graph

### Speaker notes (simple)

“The Knowledge Graph is built in the background after document text processing. Extracted concepts are shown as nodes, and their relationships are shown as labelled links. This connects concepts from the student's course material. When graph context is available in a chat response, the student can open and explore it using the graph view.”

### Technical working

1. Once the main document chunking job succeeds, a Hangfire continuation schedules graph processing.
2. The .NET chunk service calls the Python FastAPI `POST /chunk/` endpoint.
3. Python reads the already-stored document chunks, prepares graph-specific text chunks, and calls the configured language model to extract entities and typed relationships.
4. Python writes user, subject, document and entity nodes, and relationship edges to Neo4j. IDs on graph records provide user/document/subject scope and provenance.
5. The Python service stores extraction checkpoint files locally so an interrupted extraction can resume.
6. During chat, graph retrieval can return a query-relevant subgraph/context. The backend stores the returned context with the assistant message.
7. The React graph viewer transforms the returned entities and relationships into nodes and links and renders them with `react-force-graph-2d`. The viewer has zoom and fit controls. It visualizes context returned with the chat response; it does not connect directly to Neo4j.

**Technologies:** Hangfire, ASP.NET Core, Python, FastAPI, configured LLM provider, Neo4j, Cypher, Bolt, JSON checkpoints, React Force Graph 2D.

**Accuracy note:** The graph is an AI-extracted representation that complements document text. It is not a proof that a generated relationship is always correct.

### Code locations

- `Frontend/src/app/components/chat/KnowledgeGraphViewer.tsx` — graph visualization.
- `Frontend/src/app/components/chat/MessageBubble.tsx` — graph-view action on a chat response.
- `Backend/AgenticAITutor/AgenticAITutor/BackgroundJobs/DocumentChunkingJob.cs` — schedules graph processing after primary chunk processing.
- `Backend/AgenticAITutor/AgenticAITutor/Services/DocumentChunk/DocumentChunkService.cs` — sends the KG request.
- `ai_service/app/main.py` — lifespan/schema initialization and router registration.
- `ai_service/app/chunk_kg.py` — reads existing chunks and coordinates KG chunk processing.
- `ai_service/app/kg_extractor.py`, `kg_service.py`, `kg_store.py`, `kg_db.py` — extraction, graph query/write and Neo4j connection/schema.
- `Backend/AgenticAITutor/AgenticAITutor/schema.sql` — document KG processing status and chat `kg_context`.

---

## Slide 10 — Quizzes / Progress

### Speaker notes (simple)

“The student can generate a quiz from processed study documents, wait for it to become ready, and then answer the questions. After submitting, the student sees a score and can review correct answers and explanations. Quiz history keeps previous attempts available. The Progress page summarizes completed quiz performance over time and by subject.”

### Technical working — quiz flow

1. The frontend submits selected documents and requested question count to `POST /api/Quiz/initiate`.
2. The .NET service validates ownership and processing status, creates or reuses a quiz where appropriate, and queues a Hangfire generation job.
3. The background job loads `content.quiz_chunks` and sends chunk text and metadata to the Python `POST /quiz/generate` endpoint.
4. Python constructs prompts, generates and validates MCQs using the configured quiz model/provider, and returns questions. The Python generation endpoint does not persist to the app database; .NET saves question and option records.
5. The frontend polls quiz status. When a learner starts a quiz, the server creates an attempt and shuffles choices while retaining the original-label mapping.
6. Submission is scored by the backend, which saves the attempt score and individual answers. The review page retrieves and displays the outcome and explanation.

**Quiz metadata accuracy:** The normal upload job copies RAG chunks to quiz chunks with default `understand` and `definition` metadata and empty concepts/keywords. The separate `/quiz/process` endpoint is not called by the inspected normal upload path. Local fine-tuned Qwen weights are not present in this checkout; a configured external quiz provider is required unless those weights are supplied.

### Technical working — progress

- The React Progress page calls `GET /api/Analytics/progress`.
- The analytics service derives metrics from completed quiz attempts and associated quiz/answer records.
- The page shows the returned completed-quiz count, active subjects, overall score summary, monthly trend and per-subject progress.
- “Mastery” is a score-based summary in this implementation, not a separately trained knowledge model.

**Technologies:** React, Recharts, ASP.NET Core, EF Core, Hangfire, FastAPI/Pydantic, configured quiz model provider, PostgreSQL.

### Code locations

- `Frontend/src/app/pages/Quiz.tsx` — quiz list, generation and status polling.
- `Frontend/src/app/pages/QuizDetail.tsx`, `ActiveQuiz.tsx`, `QuizReview.tsx` — quiz details, attempt and review.
- `Frontend/src/app/pages/Progress.tsx` — progress dashboard and chart.
- `Frontend/src/services/quizService.ts` and `analyticsService.ts` — frontend endpoints.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/QuizController.cs` — quiz endpoints.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Quiz/QuizService.cs` — quiz lifecycle and attempt handling.
- `Backend/AgenticAITutor/AgenticAITutor/BackgroundJobs/QuizGenerationJob.cs` — AI call and persistence of generated questions.
- `Backend/AgenticAITutor/AgenticAITutor/Services/Quiz/QuizAIClient.cs` — request to Python quiz API.
- `ai_service/app/quiz/quiz_generate_router.py` and `quiz_generator.py` — MCQ generation.
- `Backend/AgenticAITutor/AgenticAITutor/Controllers/AnalyticsController.cs` and `Services/Analytics/AnalyticsService.cs` — progress endpoint/calculations.
- `Backend/AgenticAITutor/AgenticAITutor/schema.sql` — quiz tables, attempts, answers and options.

---

## Short closing script

“These screens form one learning flow: a student creates subjects for their courses, uploads the relevant files, asks questions about selected documents, explores sources and related concepts, then practices with quizzes and reviews progress. The React interface calls the .NET application API; .NET manages accounts and stored learning records and sends AI work to Python. PostgreSQL stores application and retrieval data, while Neo4j stores the concept graph.”

