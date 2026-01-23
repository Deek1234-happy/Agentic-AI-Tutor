using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quiz_questions", Schema = "quiz")]
public partial class quiz_question
{
    [Key]
    public Guid id { get; set; }

    public Guid? quiz_id { get; set; }

    public string question_text { get; set; } = null!;

    [MaxLength(1)]
    public char correct_option { get; set; }

    public string? explanation { get; set; }

    [ForeignKey("quiz_id")]
    [InverseProperty("quiz_questions")]
    public virtual quiz? quiz { get; set; }

    [InverseProperty("question")]
    public virtual ICollection<quiz_answer> quiz_answers { get; set; } = new List<quiz_answer>();

    [InverseProperty("question")]
    public virtual ICollection<quiz_option> quiz_options { get; set; } = new List<quiz_option>();

    [ForeignKey("question_id")]
    [InverseProperty("questions")]
    public virtual ICollection<document_chunk> chunks { get; set; } = new List<document_chunk>();
}
