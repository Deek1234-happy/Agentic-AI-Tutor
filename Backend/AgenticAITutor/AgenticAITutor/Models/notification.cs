using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("notifications")]
public partial class Notification
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [Column("title")]
    [StringLength(255)]
    public string? Title { get; set; }

    [Column("message")]
    public string? Message { get; set; }

    [Column("type")]
    [StringLength(50)]
    public string? Type { get; set; }

    [Column("is_read")]
    public bool? IsRead { get; set; }

    [Column("created_at", TypeName = "timestamp without time zone")]
    public DateTime? CreatedAt { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("Notifications")]
    public virtual User? User { get; set; }
}
