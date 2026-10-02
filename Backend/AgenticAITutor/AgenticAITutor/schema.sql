DO $EF$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = 'rag') THEN
        CREATE SCHEMA rag;
    END IF;
END $EF$;


DO $EF$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = 'content') THEN
        CREATE SCHEMA content;
    END IF;
END $EF$;


DO $EF$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = 'quiz') THEN
        CREATE SCHEMA quiz;
    END IF;
END $EF$;


DO $EF$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = 'planner') THEN
        CREATE SCHEMA planner;
    END IF;
END $EF$;


DO $EF$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = 'auth') THEN
        CREATE SCHEMA auth;
    END IF;
END $EF$;


CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE "ChatMessageDocumentChunk" (
    "ChunkId" uuid NOT NULL,
    "MessageId" uuid NOT NULL,
    CONSTRAINT "PK_ChatMessageDocumentChunk" PRIMARY KEY ("ChunkId", "MessageId")
);


CREATE TABLE "ChatSessionDocument" (
    "DocumentId" uuid NOT NULL,
    "SessionId" uuid NOT NULL,
    CONSTRAINT "PK_ChatSessionDocument" PRIMARY KEY ("DocumentId", "SessionId")
);


CREATE TABLE "DocumentQuiz" (
    "DocumentId" uuid NOT NULL,
    "QuizId" uuid NOT NULL,
    CONSTRAINT "PK_DocumentQuiz" PRIMARY KEY ("DocumentId", "QuizId")
);


CREATE TABLE "DocumentStudyPlan" (
    "DocumentId" uuid NOT NULL,
    "PlanId" uuid NOT NULL,
    CONSTRAINT "PK_DocumentStudyPlan" PRIMARY KEY ("DocumentId", "PlanId")
);


CREATE TABLE auth.users (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    first_name character varying(255) NOT NULL,
    last_name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    role character varying(50) DEFAULT ('user'::character varying),
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    last_login timestamp without time zone,
    password_reset_otp text,
    otp_expiry_time timestamp without time zone,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);


CREATE TABLE activity_logs (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    user_id uuid,
    action character varying(255),
    metadata jsonb,
    timestamp timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    CONSTRAINT activity_logs_pkey PRIMARY KEY (id),
    CONSTRAINT activity_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE rag.chat_sessions (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    user_id uuid,
    started_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    title character varying(255) DEFAULT ('New Chat'::character varying),
    updated_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    CONSTRAINT chat_sessions_pkey PRIMARY KEY (id),
    CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE notification_preferences (
    user_id uuid NOT NULL,
    reminder boolean DEFAULT TRUE,
    weak_topic boolean DEFAULT TRUE,
    quiz boolean DEFAULT TRUE,
    progress boolean DEFAULT TRUE,
    CONSTRAINT notification_preferences_pkey PRIMARY KEY (user_id),
    CONSTRAINT notification_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE notifications (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    user_id uuid,
    title character varying(255),
    message text,
    type character varying(50),
    is_read boolean DEFAULT FALSE,
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    CONSTRAINT notifications_pkey PRIMARY KEY (id),
    CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE planner.study_plans (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    user_id uuid,
    start_date date NOT NULL,
    end_date date NOT NULL,
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    CONSTRAINT study_plans_pkey PRIMARY KEY (id),
    CONSTRAINT study_plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE content.subjects (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    name character varying(255) NOT NULL,
    user_id uuid NOT NULL,
    CONSTRAINT subjects_pkey PRIMARY KEY (id),
    CONSTRAINT fk_subjects_user FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE user_topic_progress (
    user_id uuid NOT NULL,
    concept_ref character varying(255) NOT NULL,
    mastery_score double precision,
    last_updated timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    CONSTRAINT user_topic_progress_pkey PRIMARY KEY (user_id, concept_ref),
    CONSTRAINT user_topic_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE rag.chat_messages (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    session_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    confidence_score double precision,
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    audio_url text,
    kg_context jsonb,
    CONSTRAINT chat_messages_pkey PRIMARY KEY (id),
    CONSTRAINT chat_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES rag.chat_sessions (id) ON DELETE CASCADE
);


CREATE TABLE planner.study_plan_items (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    plan_id uuid,
    concept_ref character varying(255) NOT NULL,
    estimated_time integer,
    scheduled_date date,
    completed boolean DEFAULT FALSE,
    CONSTRAINT study_plan_items_pkey PRIMARY KEY (id),
    CONSTRAINT study_plan_items_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES planner.study_plans (id) ON DELETE CASCADE
);


CREATE TABLE content.documents (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    user_id uuid NOT NULL,
    filename character varying(255) NOT NULL,
    file_type character varying(50) NOT NULL,
    file_size integer,
    storage_path text NOT NULL,
    content_hash character(64) NOT NULL,
    upload_time timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    subject_id uuid NOT NULL,
    processing_status character varying(20) NOT NULL DEFAULT ('PENDING'::character varying),
    kg_status character varying(20),
    quiz_chunking_status character varying(20),
    CONSTRAINT documents_pkey PRIMARY KEY (id),
    CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE,
    CONSTRAINT fk_documents_subject FOREIGN KEY (subject_id) REFERENCES content.subjects (id) ON DELETE CASCADE
);


CREATE TABLE quiz.quizzes (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    user_id uuid,
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    generation_hash character(64),
    status character varying(20) NOT NULL DEFAULT ('PENDING'::character varying),
    subject_id uuid,
    question_count integer DEFAULT 0,
    generated_at timestamp without time zone,
    CONSTRAINT quizzes_pkey PRIMARY KEY (id),
    CONSTRAINT fk_quiz_subject FOREIGN KEY (subject_id) REFERENCES content.subjects (id) ON DELETE SET NULL,
    CONSTRAINT quizzes_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE rag.chat_web_sources (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    message_id uuid,
    title text,
    url text NOT NULL,
    domain character varying(255),
    CONSTRAINT chat_web_sources_pkey PRIMARY KEY (id),
    CONSTRAINT chat_web_sources_message_id_fkey FOREIGN KEY (message_id) REFERENCES rag.chat_messages (id) ON DELETE CASCADE
);


CREATE TABLE rag.chat_documents (
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    CONSTRAINT chat_documents_pkey PRIMARY KEY (session_id, document_id),
    CONSTRAINT fk_document FOREIGN KEY (document_id) REFERENCES content.documents (id) ON DELETE CASCADE,
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES rag.chat_sessions (id) ON DELETE CASCADE
);


CREATE TABLE content.document_chunks (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    document_id uuid,
    chunk_text text NOT NULL,
    page_start integer,
    page_end integer,
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    subject_id uuid,
    user_id uuid,
    embedding vector(768),
    CONSTRAINT document_chunks_pkey PRIMARY KEY (id),
    CONSTRAINT "FK_DocumentChunks_Subjects_subject_id" FOREIGN KEY (subject_id) REFERENCES content.subjects (id) ON DELETE CASCADE,
    CONSTRAINT "FK_DocumentChunks_isers_usert_id" FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE,
    CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES content.documents (id) ON DELETE CASCADE
);


CREATE TABLE content.quiz_chunks (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    document_id uuid,
    chunk_index integer NOT NULL,
    chunk_text text NOT NULL,
    context_prev_sentence text,
    context_next_sentence text,
    semantic_score double precision,
    quality_score double precision,
    bloom_level character varying(50),
    chunk_type character varying(50),
    concepts text[] DEFAULT ('{}'::text[]),
    keywords text[] DEFAULT ('{}'::text[]),
    created_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    subject_id uuid,
    user_id uuid,
    CONSTRAINT quiz_chunks_pkey PRIMARY KEY (id),
    CONSTRAINT fk_quiz_chunks_document FOREIGN KEY (document_id) REFERENCES content.documents (id) ON DELETE CASCADE,
    CONSTRAINT fk_quiz_chunks_subject FOREIGN KEY (subject_id) REFERENCES content.subjects (id) ON DELETE CASCADE,
    CONSTRAINT fk_quiz_chunks_user FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE planner.study_plan_documents (
    plan_id uuid NOT NULL,
    document_id uuid NOT NULL,
    CONSTRAINT study_plan_documents_pkey PRIMARY KEY (plan_id, document_id),
    CONSTRAINT study_plan_documents_document_id_fkey FOREIGN KEY (document_id) REFERENCES content.documents (id) ON DELETE CASCADE,
    CONSTRAINT study_plan_documents_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES planner.study_plans (id) ON DELETE CASCADE
);


CREATE TABLE quiz.quiz_attempts (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    quiz_id uuid,
    user_id uuid,
    score double precision,
    started_at timestamp without time zone DEFAULT (CURRENT_TIMESTAMP),
    finished_at timestamp without time zone,
    attempt_number integer NOT NULL DEFAULT 1,
    shuffle_mapping jsonb,
    CONSTRAINT quiz_attempts_pkey PRIMARY KEY (id),
    CONSTRAINT quiz_attempts_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES quiz.quizzes (id) ON DELETE CASCADE,
    CONSTRAINT quiz_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);


CREATE TABLE quiz.quiz_documents (
    quiz_id uuid NOT NULL,
    document_id uuid NOT NULL,
    CONSTRAINT quiz_documents_pkey PRIMARY KEY (quiz_id, document_id),
    CONSTRAINT fk_qd_document FOREIGN KEY (document_id) REFERENCES content.documents (id) ON DELETE CASCADE,
    CONSTRAINT fk_qd_quiz FOREIGN KEY (quiz_id) REFERENCES quiz.quizzes (id) ON DELETE CASCADE
);


CREATE TABLE rag.chat_citations (
    message_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    CONSTRAINT chat_citations_pkey PRIMARY KEY (message_id, chunk_id),
    CONSTRAINT chat_citations_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES content.document_chunks (id) ON DELETE CASCADE,
    CONSTRAINT chat_citations_message_id_fkey FOREIGN KEY (message_id) REFERENCES rag.chat_messages (id) ON DELETE CASCADE
);


CREATE TABLE quiz.quiz_questions (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    quiz_id uuid,
    question_text text NOT NULL,
    correct_option character(1) NOT NULL,
    explanation text,
    concept character varying(255),
    bloom_level character varying(50),
    slot_index integer DEFAULT 0,
    chunk_id uuid,
    CONSTRAINT quiz_questions_pkey PRIMARY KEY (id),
    CONSTRAINT fk_quiz_questions_quiz_chunks FOREIGN KEY (chunk_id) REFERENCES content.quiz_chunks (id) ON DELETE SET NULL,
    CONSTRAINT quiz_questions_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES quiz.quizzes (id) ON DELETE CASCADE
);


CREATE TABLE quiz.quiz_answers (
    attempt_id uuid NOT NULL,
    question_id uuid NOT NULL,
    selected_option character(1),
    is_correct boolean,
    CONSTRAINT quiz_answers_pkey PRIMARY KEY (attempt_id, question_id),
    CONSTRAINT quiz_answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES quiz.quiz_attempts (id) ON DELETE CASCADE,
    CONSTRAINT quiz_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES quiz.quiz_questions (id) ON DELETE CASCADE
);


CREATE TABLE quiz.quiz_options (
    id uuid NOT NULL DEFAULT (uuid_generate_v4()),
    question_id uuid,
    option_label character(1),
    option_text text NOT NULL,
    CONSTRAINT quiz_options_pkey PRIMARY KEY (id),
    CONSTRAINT quiz_options_question_id_fkey FOREIGN KEY (question_id) REFERENCES quiz.quiz_questions (id) ON DELETE CASCADE
);


CREATE INDEX "IX_activity_logs_user_id" ON activity_logs (user_id);


CREATE INDEX "IX_chat_citations_chunk_id" ON rag.chat_citations (chunk_id);


CREATE INDEX "IX_chat_documents_document_id" ON rag.chat_documents (document_id);


CREATE INDEX "IX_chat_messages_session_id" ON rag.chat_messages (session_id);


CREATE INDEX "IX_chat_sessions_user_id" ON rag.chat_sessions (user_id);


CREATE INDEX "IX_chat_web_sources_message_id" ON rag.chat_web_sources (message_id);


CREATE INDEX "IX_document_chunks_document_id" ON content.document_chunks (document_id);


CREATE INDEX "IX_document_chunks_subject_id" ON content.document_chunks (subject_id);


CREATE INDEX "IX_document_chunks_user_id" ON content.document_chunks (user_id);


CREATE UNIQUE INDEX documents_user_id_content_hash_key ON content.documents (user_id, content_hash);


CREATE INDEX "IX_documents_subject_id" ON content.documents (subject_id);


CREATE INDEX "IX_notifications_user_id" ON notifications (user_id);


CREATE INDEX "IX_quiz_answers_question_id" ON quiz.quiz_answers (question_id);


CREATE INDEX idx_attempt_user_quiz_date ON quiz.quiz_attempts (user_id, quiz_id, started_at DESC);


CREATE INDEX "IX_quiz_attempts_quiz_id" ON quiz.quiz_attempts (quiz_id);


CREATE INDEX "IX_quiz_chunks_document_id" ON content.quiz_chunks (document_id);


CREATE INDEX "IX_quiz_chunks_subject_id" ON content.quiz_chunks (subject_id);


CREATE INDEX "IX_quiz_chunks_user_id" ON content.quiz_chunks (user_id);


CREATE INDEX idx_quiz_docs_document ON quiz.quiz_documents (document_id);


CREATE INDEX "IX_quiz_options_question_id" ON quiz.quiz_options (question_id);


CREATE INDEX idx_quiz_questions_quiz_slot ON quiz.quiz_questions (quiz_id, slot_index);


CREATE INDEX "IX_quiz_questions_chunk_id" ON quiz.quiz_questions (chunk_id);


CREATE INDEX idx_quiz_status ON quiz.quizzes (status);


CREATE INDEX idx_quiz_subject_user ON quiz.quizzes (subject_id, user_id);


CREATE INDEX idx_quiz_user_hash ON quiz.quizzes (user_id, generation_hash);


CREATE UNIQUE INDEX uq_quiz_user_hash ON quiz.quizzes (user_id, generation_hash);


CREATE INDEX "IX_study_plan_documents_document_id" ON planner.study_plan_documents (document_id);


CREATE INDEX "IX_study_plan_items_plan_id" ON planner.study_plan_items (plan_id);


CREATE INDEX "IX_study_plans_user_id" ON planner.study_plans (user_id);


CREATE UNIQUE INDEX unique_subject_per_user ON content.subjects (user_id, name);


CREATE UNIQUE INDEX users_email_key ON auth.users (email);


