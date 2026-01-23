using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[PrimaryKey("user_id", "concept_ref")]
[Table("user_topic_progress")]
public partial class user_topic_progress
{
    [Key]
    public Guid user_id { get; set; }

    [Key]
    [StringLength(255)]
    public string concept_ref { get; set; } = null!;

    public double? mastery_score { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? last_updated { get; set; }

    [ForeignKey("user_id")]
    [InverseProperty("user_topic_progresses")]
    public virtual user user { get; set; } = null!;
}
