using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("activity_logs")]
public partial class ActivityLog
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [Column("action")]
    [StringLength(255)]
    public string? Action { get; set; }

    [Column("metadata", TypeName = "jsonb")]
    public string? Metadata { get; set; }

    [Column("timestamp", TypeName = "timestamp without time zone")]
    public DateTime? Timestamp { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("ActivityLogs")]
    public virtual User? User { get; set; }
}
