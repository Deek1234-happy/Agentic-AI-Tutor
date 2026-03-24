using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("chat_messages", Schema = "rag")]
public partial class ChatMessage
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("session_id")]
    public Guid? SessionId { get; set; }

    [Column("role")]
    [StringLength(20)]
    public string Role { get; set; } = null!;

    [Column("content")]
    public string Content { get; set; } = null!;

    [Column("confidence_score")]
    public double? ConfidenceScore { get; set; }

    [Column("created_at", TypeName = "timestamp without time zone")]
    public DateTime? CreatedAt { get; set; }

    [InverseProperty("Message")]
    public virtual ICollection<ChatWebSource> ChatWebSources { get; set; } = new List<ChatWebSource>();

    [ForeignKey("SessionId")]
    [InverseProperty("ChatMessages")]
    public virtual ChatSession? Session { get; set; }

    [ForeignKey("MessageId")]
    [InverseProperty("Messages")]
    public virtual ICollection<DocumentChunk> Chunks { get; set; } = new List<DocumentChunk>();
}
