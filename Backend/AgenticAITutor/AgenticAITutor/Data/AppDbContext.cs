using System;
using System.Collections.Generic;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Data;

public partial class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options)
        : base(options)
    {
    }

    public virtual DbSet<ActivityLog> ActivityLogs { get; set; }

    public virtual DbSet<ChatMessage> ChatMessages { get; set; }

    public virtual DbSet<ChatSession> ChatSessions { get; set; }

    public virtual DbSet<Document> Documents { get; set; }

    public virtual DbSet<DocumentChunk> DocumentChunks { get; set; }

    public virtual DbSet<Notification> Notifications { get; set; }

    public virtual DbSet<NotificationPreference> NotificationPreferences { get; set; }

    public virtual DbSet<Quiz> Quizzes { get; set; }

    public virtual DbSet<QuizAnswer> QuizAnswers { get; set; }

    public virtual DbSet<QuizAttempt> QuizAttempts { get; set; }

    public virtual DbSet<QuizOption> QuizOptions { get; set; }

    public virtual DbSet<QuizQuestion> QuizQuestions { get; set; }

    public virtual DbSet<StudyPlan> StudyPlans { get; set; }

    public virtual DbSet<StudyPlanItem> StudyPlanItems { get; set; }

    public virtual DbSet<Subject> Subjects { get; set; }

    public virtual DbSet<User> Users { get; set; }

    public virtual DbSet<UserTopicProgress> UserTopicProgresses { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder
            .HasPostgresExtension("uuid-ossp")
            .HasPostgresExtension("vector");

        modelBuilder.Entity<ActivityLog>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("activity_logs_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.Timestamp).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.User).WithMany(p => p.ActivityLogs)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("activity_logs_user_id_fkey");
        });

        modelBuilder.Entity<ChatMessage>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("chat_messages_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.Session).WithMany(p => p.ChatMessages)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("chat_messages_session_id_fkey");

            entity.HasMany(d => d.Chunks).WithMany(p => p.Messages)
                .UsingEntity<Dictionary<string, object>>(
                    "ChatCitation",
                    r => r.HasOne<DocumentChunk>().WithMany()
                        .HasForeignKey("ChunkId")
                        .HasConstraintName("chat_citations_chunk_id_fkey"),
                    l => l.HasOne<ChatMessage>().WithMany()
                        .HasForeignKey("MessageId")
                        .HasConstraintName("chat_citations_message_id_fkey"),
                    j =>
                    {
                        j.HasKey("MessageId", "ChunkId").HasName("chat_citations_pkey");
                        j.ToTable("chat_citations", "rag");
                        j.IndexerProperty<Guid>("MessageId").HasColumnName("message_id");
                        j.IndexerProperty<Guid>("ChunkId").HasColumnName("chunk_id");
                    });
        });

        modelBuilder.Entity<ChatSession>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("chat_sessions_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.StartedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.User).WithMany(p => p.ChatSessions)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("chat_sessions_user_id_fkey");
        });

        modelBuilder.Entity<Document>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("documents_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.ContentHash).IsFixedLength();
            entity.Property(e => e.IsDeleted).HasDefaultValue(false);
            entity.Property(e => e.ProcessingStatus).HasDefaultValueSql("'PENDING'::character varying");
            entity.Property(e => e.UploadTime).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.Subject).WithMany(p => p.Documents)
                .OnDelete(DeleteBehavior.Restrict)
                .HasConstraintName("fk_documents_subject");

            entity.HasOne(d => d.User).WithMany(p => p.Documents).HasConstraintName("documents_user_id_fkey");
        });

        modelBuilder.Entity<DocumentChunk>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("document_chunks_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.Document).WithMany(p => p.DocumentChunks)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("document_chunks_document_id_fkey");

            entity.HasOne(d => d.Subject).WithMany(p => p.DocumentChunks)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("FK_DocumentChunks_Subjects_subject_id");

            entity.HasOne(d => d.User).WithMany(p => p.DocumentChunks)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("FK_DocumentChunks_isers_usert_id");
        });

        modelBuilder.Entity<Notification>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("notifications_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
            entity.Property(e => e.IsRead).HasDefaultValue(false);

            entity.HasOne(d => d.User).WithMany(p => p.Notifications)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("notifications_user_id_fkey");
        });

        modelBuilder.Entity<NotificationPreference>(entity =>
        {
            entity.HasKey(e => e.UserId).HasName("notification_preferences_pkey");

            entity.Property(e => e.UserId).ValueGeneratedNever();
            entity.Property(e => e.Progress).HasDefaultValue(true);
            entity.Property(e => e.Quiz).HasDefaultValue(true);
            entity.Property(e => e.Reminder).HasDefaultValue(true);
            entity.Property(e => e.WeakTopic).HasDefaultValue(true);

            entity.HasOne(d => d.User).WithOne(p => p.NotificationPreference).HasConstraintName("notification_preferences_user_id_fkey");
        });

        modelBuilder.Entity<Quiz>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("quizzes_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.User).WithMany(p => p.Quizzes)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quizzes_user_id_fkey");
        });

        modelBuilder.Entity<QuizAnswer>(entity =>
        {
            entity.HasKey(e => new { e.AttemptId, e.QuestionId }).HasName("quiz_answers_pkey");

            entity.HasOne(d => d.Attempt).WithMany(p => p.QuizAnswers).HasConstraintName("quiz_answers_attempt_id_fkey");

            entity.HasOne(d => d.Question).WithMany(p => p.QuizAnswers).HasConstraintName("quiz_answers_question_id_fkey");
        });

        modelBuilder.Entity<QuizAttempt>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("quiz_attempts_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.TakenAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.Quiz).WithMany(p => p.QuizAttempts)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_attempts_quiz_id_fkey");

            entity.HasOne(d => d.User).WithMany(p => p.QuizAttempts)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_attempts_user_id_fkey");
        });

        modelBuilder.Entity<QuizOption>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("quiz_options_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");

            entity.HasOne(d => d.Question).WithMany(p => p.QuizOptions)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_options_question_id_fkey");
        });

        modelBuilder.Entity<QuizQuestion>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("quiz_questions_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");

            entity.HasOne(d => d.Quiz).WithMany(p => p.QuizQuestions)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_questions_quiz_id_fkey");

            entity.HasMany(d => d.Chunks).WithMany(p => p.Questions)
                .UsingEntity<Dictionary<string, object>>(
                    "QuizCitation",
                    r => r.HasOne<DocumentChunk>().WithMany()
                        .HasForeignKey("ChunkId")
                        .HasConstraintName("quiz_citations_chunk_id_fkey"),
                    l => l.HasOne<QuizQuestion>().WithMany()
                        .HasForeignKey("QuestionId")
                        .HasConstraintName("quiz_citations_question_id_fkey"),
                    j =>
                    {
                        j.HasKey("QuestionId", "ChunkId").HasName("quiz_citations_pkey");
                        j.ToTable("quiz_citations", "quiz");
                        j.IndexerProperty<Guid>("QuestionId").HasColumnName("question_id");
                        j.IndexerProperty<Guid>("ChunkId").HasColumnName("chunk_id");
                    });
        });

        modelBuilder.Entity<StudyPlan>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("study_plans_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.User).WithMany(p => p.StudyPlans)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("study_plans_user_id_fkey");

            entity.HasMany(d => d.Documents).WithMany(p => p.Plans)
                .UsingEntity<Dictionary<string, object>>(
                    "StudyPlanDocument",
                    r => r.HasOne<Document>().WithMany()
                        .HasForeignKey("DocumentId")
                        .HasConstraintName("study_plan_documents_document_id_fkey"),
                    l => l.HasOne<StudyPlan>().WithMany()
                        .HasForeignKey("PlanId")
                        .HasConstraintName("study_plan_documents_plan_id_fkey"),
                    j =>
                    {
                        j.HasKey("PlanId", "DocumentId").HasName("study_plan_documents_pkey");
                        j.ToTable("study_plan_documents", "planner");
                        j.IndexerProperty<Guid>("PlanId").HasColumnName("plan_id");
                        j.IndexerProperty<Guid>("DocumentId").HasColumnName("document_id");
                    });
        });

        modelBuilder.Entity<StudyPlanItem>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("study_plan_items_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.Completed).HasDefaultValue(false);

            entity.HasOne(d => d.Plan).WithMany(p => p.StudyPlanItems)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("study_plan_items_plan_id_fkey");
        });

        modelBuilder.Entity<Subject>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("subjects_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");

            entity.HasOne(d => d.User).WithMany(p => p.Subjects).HasConstraintName("fk_subjects_user");
        });

        modelBuilder.Entity<User>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("users_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
            entity.Property(e => e.Role).HasDefaultValueSql("'user'::character varying");
        });

        modelBuilder.Entity<UserTopicProgress>(entity =>
        {
            entity.HasKey(e => new { e.UserId, e.ConceptRef }).HasName("user_topic_progress_pkey");

            entity.Property(e => e.LastUpdated).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.User).WithMany(p => p.UserTopicProgresses).HasConstraintName("user_topic_progress_user_id_fkey");
        });

        OnModelCreatingPartial(modelBuilder);
    }

    partial void OnModelCreatingPartial(ModelBuilder modelBuilder);
}
