using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Models;

[Table("quiz_options", Schema = "quiz")]
public partial class quiz_option
{
    [Key]
    public Guid id { get; set; }

    public Guid? question_id { get; set; }

    [MaxLength(1)]
    public char? option_label { get; set; }

    public string option_text { get; set; } = null!;

    [ForeignKey("question_id")]
    [InverseProperty("quiz_options")]
    public virtual quiz_question? question { get; set; }
}
