using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Models;

[Table("quiz_attempts", Schema = "quiz")]
public partial class quiz_attempt
{
    [Key]
    public Guid id { get; set; }

    public Guid? quiz_id { get; set; }

    public Guid? user_id { get; set; }

    public double? score { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? taken_at { get; set; }

    [ForeignKey("quiz_id")]
    [InverseProperty("quiz_attempts")]
    public virtual quiz? quiz { get; set; }

    [InverseProperty("attempt")]
    public virtual ICollection<quiz_answer> quiz_answers { get; set; } = new List<quiz_answer>();

    [ForeignKey("user_id")]
    [InverseProperty("quiz_attempts")]
    public virtual user? user { get; set; }
}
