using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[PrimaryKey("AttemptId", "QuestionId")]
[Table("quiz_answers", Schema = "quiz")]
public partial class QuizAnswer
{
    [Key]
    [Column("attempt_id")]
    public Guid AttemptId { get; set; }

    [Key]
    [Column("question_id")]
    public Guid QuestionId { get; set; }

    [Column("selected_option")]
    [MaxLength(1)]
    public char? SelectedOption { get; set; }

    [Column("is_correct")]
    public bool? IsCorrect { get; set; }

    [ForeignKey("AttemptId")]
    [InverseProperty("QuizAnswers")]
    public virtual QuizAttempt Attempt { get; set; } = null!;

    [ForeignKey("QuestionId")]
    [InverseProperty("QuizAnswers")]
    public virtual QuizQuestion Question { get; set; } = null!;
}
