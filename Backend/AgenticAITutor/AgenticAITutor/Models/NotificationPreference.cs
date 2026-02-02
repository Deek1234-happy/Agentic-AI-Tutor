using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("notification_preferences")]
public partial class NotificationPreference
{
    [Key]
    [Column("user_id")]
    public Guid UserId { get; set; }

    [Column("reminder")]
    public bool? Reminder { get; set; }

    [Column("weak_topic")]
    public bool? WeakTopic { get; set; }

    [Column("quiz")]
    public bool? Quiz { get; set; }

    [Column("progress")]
    public bool? Progress { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("NotificationPreference")]
    public virtual User User { get; set; } = null!;
}
