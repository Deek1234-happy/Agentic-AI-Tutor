using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[PrimaryKey("attempt_id", "question_id")]
[Table("quiz_answers", Schema = "quiz")]
public partial class quiz_answer
{
    [Key]
    public Guid attempt_id { get; set; }

    [Key]
    public Guid question_id { get; set; }

    [MaxLength(1)]
    public char? selected_option { get; set; }

    public bool? is_correct { get; set; }

    [ForeignKey("attempt_id")]
    [InverseProperty("quiz_answers")]
    public virtual quiz_attempt attempt { get; set; } = null!;

    [ForeignKey("question_id")]
    [InverseProperty("quiz_answers")]
    public virtual quiz_question question { get; set; } = null!;
}
