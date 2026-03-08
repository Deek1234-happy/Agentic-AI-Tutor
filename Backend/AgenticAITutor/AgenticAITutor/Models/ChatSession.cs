using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("chat_sessions", Schema = "rag")]
public partial class ChatSession
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [Column("started_at", TypeName = "timestamp without time zone")]
    public DateTime? StartedAt { get; set; }

    [Column("title")]
    [StringLength(255)]
    public string? Title { get; set; }

    [Column("updated_at", TypeName = "timestamp without time zone")]
    public DateTime? UpdatedAt { get; set; }

    [InverseProperty("Session")]
    public virtual ICollection<ChatMessage> ChatMessages { get; set; } = new List<ChatMessage>();

    [ForeignKey("UserId")]
    [InverseProperty("ChatSessions")]
    public virtual User? User { get; set; }

    [ForeignKey("SessionId")]
    [InverseProperty("Sessions")]
    public virtual ICollection<Document> Documents { get; set; } = new List<Document>();
}
