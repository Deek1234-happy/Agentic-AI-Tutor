using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[PrimaryKey("UserId", "ConceptRef")]
[Table("user_topic_progress")]
public partial class UserTopicProgress
{
    [Key]
    [Column("user_id")]
    public Guid UserId { get; set; }

    [Key]
    [Column("concept_ref")]
    [StringLength(255)]
    public string ConceptRef { get; set; } = null!;

    [Column("mastery_score")]
    public double? MasteryScore { get; set; }

    [Column("last_updated", TypeName = "timestamp without time zone")]
    public DateTime? LastUpdated { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("UserTopicProgresses")]
    public virtual User User { get; set; } = null!;
}
