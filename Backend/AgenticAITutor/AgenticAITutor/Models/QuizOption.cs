using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quiz_options", Schema = "quiz")]
public partial class QuizOption
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("question_id")]
    public Guid? QuestionId { get; set; }

    [Column("option_label")]
    [MaxLength(1)]
    public char? OptionLabel { get; set; }

    [Column("option_text")]
    public string OptionText { get; set; } = null!;

    [ForeignKey("QuestionId")]
    [InverseProperty("QuizOptions")]
    public virtual QuizQuestion? Question { get; set; }
}
