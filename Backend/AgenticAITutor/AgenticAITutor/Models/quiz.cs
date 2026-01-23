using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quizzes", Schema = "quiz")]
public partial class quiz
{
    [Key]
    public Guid id { get; set; }

    public Guid? user_id { get; set; }

    [StringLength(255)]
    public string? topic { get; set; }

    [StringLength(50)]
    public string? difficulty { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? created_at { get; set; }

    [InverseProperty("quiz")]
    public virtual ICollection<quiz_attempt> quiz_attempts { get; set; } = new List<quiz_attempt>();

    [InverseProperty("quiz")]
    public virtual ICollection<quiz_question> quiz_questions { get; set; } = new List<quiz_question>();

    [ForeignKey("user_id")]
    [InverseProperty("quizzes")]
    public virtual user? user { get; set; }
}
