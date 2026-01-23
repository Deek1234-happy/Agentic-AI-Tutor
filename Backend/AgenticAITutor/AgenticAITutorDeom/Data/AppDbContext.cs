using System;
using System.Collections.Generic;
using AgenticAITutorDeom.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Data;

public partial class AppDbContext : DbContext
{
    public AppDbContext()
    {
    }

    public AppDbContext(DbContextOptions<AppDbContext> options)
        : base(options)
    {
    }

    public virtual DbSet<activity_log> activity_logs { get; set; }

    public virtual DbSet<chat_message> chat_messages { get; set; }

    public virtual DbSet<chat_session> chat_sessions { get; set; }

    public virtual DbSet<document> documents { get; set; }

    public virtual DbSet<document_chunk> document_chunks { get; set; }

    public virtual DbSet<notification> notifications { get; set; }

    public virtual DbSet<notification_preference> notification_preferences { get; set; }

    public virtual DbSet<quiz> quizzes { get; set; }

    public virtual DbSet<quiz_answer> quiz_answers { get; set; }

    public virtual DbSet<quiz_attempt> quiz_attempts { get; set; }

    public virtual DbSet<quiz_option> quiz_options { get; set; }

    public virtual DbSet<quiz_question> quiz_questions { get; set; }

    public virtual DbSet<study_plan> study_plans { get; set; }

    public virtual DbSet<study_plan_item> study_plan_items { get; set; }

    public virtual DbSet<user> users { get; set; }

    public virtual DbSet<user_topic_progress> user_topic_progresses { get; set; }

   
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder
            .HasPostgresExtension("uuid-ossp")
            .HasPostgresExtension("vector");

        modelBuilder.Entity<activity_log>(entity =>
        {
            entity.HasKey(e => e.id).HasName("activity_logs_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.timestamp).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.user).WithMany(p => p.activity_logs)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("activity_logs_user_id_fkey");
        });

        modelBuilder.Entity<chat_message>(entity =>
        {
            entity.HasKey(e => e.id).HasName("chat_messages_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.created_at).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.session).WithMany(p => p.chat_messages)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("chat_messages_session_id_fkey");

            entity.HasMany(d => d.chunks).WithMany(p => p.messages)
                .UsingEntity<Dictionary<string, object>>(
                    "chat_citation",
                    r => r.HasOne<document_chunk>().WithMany()
                        .HasForeignKey("chunk_id")
                        .HasConstraintName("chat_citations_chunk_id_fkey"),
                    l => l.HasOne<chat_message>().WithMany()
                        .HasForeignKey("message_id")
                        .HasConstraintName("chat_citations_message_id_fkey"),
                    j =>
                    {
                        j.HasKey("message_id", "chunk_id").HasName("chat_citations_pkey");
                        j.ToTable("chat_citations", "rag");
                    });
        });

        modelBuilder.Entity<chat_session>(entity =>
        {
            entity.HasKey(e => e.id).HasName("chat_sessions_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.started_at).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.user).WithMany(p => p.chat_sessions)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("chat_sessions_user_id_fkey");
        });

        modelBuilder.Entity<document>(entity =>
        {
            entity.HasKey(e => e.id).HasName("documents_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.content_hash).IsFixedLength();
            entity.Property(e => e.is_deleted).HasDefaultValue(false);
            entity.Property(e => e.upload_time).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.user).WithMany(p => p.documents)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("documents_user_id_fkey");
        });

        modelBuilder.Entity<document_chunk>(entity =>
        {
            entity.HasKey(e => e.id).HasName("document_chunks_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.created_at).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.document).WithMany(p => p.document_chunks)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("document_chunks_document_id_fkey");
        });

        modelBuilder.Entity<notification>(entity =>
        {
            entity.HasKey(e => e.id).HasName("notifications_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.created_at).HasDefaultValueSql("CURRENT_TIMESTAMP");
            entity.Property(e => e.is_read).HasDefaultValue(false);

            entity.HasOne(d => d.user).WithMany(p => p.notifications)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("notifications_user_id_fkey");
        });

        modelBuilder.Entity<notification_preference>(entity =>
        {
            entity.HasKey(e => e.user_id).HasName("notification_preferences_pkey");

            entity.Property(e => e.user_id).ValueGeneratedNever();
            entity.Property(e => e.progress).HasDefaultValue(true);
            entity.Property(e => e.quiz).HasDefaultValue(true);
            entity.Property(e => e.reminder).HasDefaultValue(true);
            entity.Property(e => e.weak_topic).HasDefaultValue(true);

            entity.HasOne(d => d.user).WithOne(p => p.notification_preference).HasConstraintName("notification_preferences_user_id_fkey");
        });

        modelBuilder.Entity<quiz>(entity =>
        {
            entity.HasKey(e => e.id).HasName("quizzes_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.created_at).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.user).WithMany(p => p.quizzes)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quizzes_user_id_fkey");
        });

        modelBuilder.Entity<quiz_answer>(entity =>
        {
            entity.HasKey(e => new { e.attempt_id, e.question_id }).HasName("quiz_answers_pkey");

            entity.HasOne(d => d.attempt).WithMany(p => p.quiz_answers).HasConstraintName("quiz_answers_attempt_id_fkey");

            entity.HasOne(d => d.question).WithMany(p => p.quiz_answers).HasConstraintName("quiz_answers_question_id_fkey");
        });

        modelBuilder.Entity<quiz_attempt>(entity =>
        {
            entity.HasKey(e => e.id).HasName("quiz_attempts_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.taken_at).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.quiz).WithMany(p => p.quiz_attempts)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_attempts_quiz_id_fkey");

            entity.HasOne(d => d.user).WithMany(p => p.quiz_attempts)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_attempts_user_id_fkey");
        });

        modelBuilder.Entity<quiz_option>(entity =>
        {
            entity.HasKey(e => e.id).HasName("quiz_options_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");

            entity.HasOne(d => d.question).WithMany(p => p.quiz_options)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_options_question_id_fkey");
        });

        modelBuilder.Entity<quiz_question>(entity =>
        {
            entity.HasKey(e => e.id).HasName("quiz_questions_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");

            entity.HasOne(d => d.quiz).WithMany(p => p.quiz_questions)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("quiz_questions_quiz_id_fkey");

            entity.HasMany(d => d.chunks).WithMany(p => p.questions)
                .UsingEntity<Dictionary<string, object>>(
                    "quiz_citation",
                    r => r.HasOne<document_chunk>().WithMany()
                        .HasForeignKey("chunk_id")
                        .HasConstraintName("quiz_citations_chunk_id_fkey"),
                    l => l.HasOne<quiz_question>().WithMany()
                        .HasForeignKey("question_id")
                        .HasConstraintName("quiz_citations_question_id_fkey"),
                    j =>
                    {
                        j.HasKey("question_id", "chunk_id").HasName("quiz_citations_pkey");
                        j.ToTable("quiz_citations", "quiz");
                    });
        });

        modelBuilder.Entity<study_plan>(entity =>
        {
            entity.HasKey(e => e.id).HasName("study_plans_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.created_at).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.user).WithMany(p => p.study_plans)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("study_plans_user_id_fkey");

            entity.HasMany(d => d.documents).WithMany(p => p.plans)
                .UsingEntity<Dictionary<string, object>>(
                    "study_plan_document",
                    r => r.HasOne<document>().WithMany()
                        .HasForeignKey("document_id")
                        .HasConstraintName("study_plan_documents_document_id_fkey"),
                    l => l.HasOne<study_plan>().WithMany()
                        .HasForeignKey("plan_id")
                        .HasConstraintName("study_plan_documents_plan_id_fkey"),
                    j =>
                    {
                        j.HasKey("plan_id", "document_id").HasName("study_plan_documents_pkey");
                        j.ToTable("study_plan_documents", "planner");
                    });
        });

        modelBuilder.Entity<study_plan_item>(entity =>
        {
            entity.HasKey(e => e.id).HasName("study_plan_items_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.completed).HasDefaultValue(false);

            entity.HasOne(d => d.plan).WithMany(p => p.study_plan_items)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("study_plan_items_plan_id_fkey");
        });

        modelBuilder.Entity<user>(entity =>
        {
            entity.HasKey(e => e.id).HasName("users_pkey");

            entity.Property(e => e.id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.created_at).HasDefaultValueSql("CURRENT_TIMESTAMP");
            entity.Property(e => e.role).HasDefaultValueSql("'user'::character varying");
        });

        modelBuilder.Entity<user_topic_progress>(entity =>
        {
            entity.HasKey(e => new { e.user_id, e.concept_ref }).HasName("user_topic_progress_pkey");

            entity.Property(e => e.last_updated).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(d => d.user).WithMany(p => p.user_topic_progresses).HasConstraintName("user_topic_progress_user_id_fkey");
        });

        OnModelCreatingPartial(modelBuilder);
    }

    partial void OnModelCreatingPartial(ModelBuilder modelBuilder);
}
