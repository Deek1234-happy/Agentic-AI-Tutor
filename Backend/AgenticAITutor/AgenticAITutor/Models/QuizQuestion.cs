using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quiz_questions", Schema = "quiz")]
public partial class QuizQuestion
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("quiz_id")]
    public Guid? QuizId { get; set; }

    [Column("question_text")]
    public string QuestionText { get; set; } = null!;

    [Column("correct_option")]
    [MaxLength(1)]
    public char CorrectOption { get; set; }

    [Column("explanation")]
    public string? Explanation { get; set; }

    [ForeignKey("QuizId")]
    [InverseProperty("QuizQuestions")]
    public virtual Quiz? Quiz { get; set; }

    [InverseProperty("Question")]
    public virtual ICollection<QuizAnswer> QuizAnswers { get; set; } = new List<QuizAnswer>();

    [InverseProperty("Question")]
    public virtual ICollection<QuizOption> QuizOptions { get; set; } = new List<QuizOption>();

    [ForeignKey("QuestionId")]
    [InverseProperty("Questions")]
    public virtual ICollection<DocumentChunk> Chunks { get; set; } = new List<DocumentChunk>();
}
