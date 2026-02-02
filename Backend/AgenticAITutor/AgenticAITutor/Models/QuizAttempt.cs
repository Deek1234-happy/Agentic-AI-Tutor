using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quiz_attempts", Schema = "quiz")]
public partial class QuizAttempt
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("quiz_id")]
    public Guid? QuizId { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [Column("score")]
    public double? Score { get; set; }

    [Column("taken_at", TypeName = "timestamp without time zone")]
    public DateTime? TakenAt { get; set; }

    [ForeignKey("QuizId")]
    [InverseProperty("QuizAttempts")]
    public virtual Quiz? Quiz { get; set; }

    [InverseProperty("Attempt")]
    public virtual ICollection<QuizAnswer> QuizAnswers { get; set; } = new List<QuizAnswer>();

    [ForeignKey("UserId")]
    [InverseProperty("QuizAttempts")]
    public virtual User? User { get; set; }
}
