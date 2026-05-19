using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quizzes", Schema = "quiz")]
[Index("Status", Name = "idx_quiz_status")]
[Index("SubjectId", "UserId", Name = "idx_quiz_subject_user")]
[Index("UserId", "GenerationHash", Name = "idx_quiz_user_hash")]
[Index("UserId", "GenerationHash", Name = "uq_quiz_user_hash", IsUnique = true)]
public partial class Quiz
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [Column("created_at", TypeName = "timestamp without time zone")]
    public DateTime? CreatedAt { get; set; }

    [Column("generation_hash")]
    [StringLength(64)]
    public string? GenerationHash { get; set; }

    [Column("status")]
    [StringLength(20)]
    public string Status { get; set; } = null!;

    [Column("subject_id")]
    public Guid? SubjectId { get; set; }

    [Column("question_count")]
    public int? QuestionCount { get; set; }

    [Column("generated_at", TypeName = "timestamp without time zone")]
    public DateTime? GeneratedAt { get; set; }

    [InverseProperty("Quiz")]
    public virtual ICollection<QuizAttempt> QuizAttempts { get; set; } = new List<QuizAttempt>();

    [InverseProperty("Quiz")]
    public virtual ICollection<QuizQuestion> QuizQuestions { get; set; } = new List<QuizQuestion>();

    [ForeignKey("SubjectId")]
    [InverseProperty("Quizzes")]
    public virtual Subject? Subject { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("Quizzes")]
    public virtual User? User { get; set; }

    [ForeignKey("QuizId")]
    [InverseProperty("Quizzes")]
    public virtual ICollection<Document> Documents { get; set; } = new List<Document>();
}
