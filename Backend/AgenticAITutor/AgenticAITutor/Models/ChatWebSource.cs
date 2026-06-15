using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("chat_web_sources", Schema = "rag")]
public partial class ChatWebSource
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("message_id")]
    public Guid? MessageId { get; set; }

    [Column("title")]
    public string? Title { get; set; }

    [Column("url")]
    public string Url { get; set; } = null!;

    [Column("domain")]
    [StringLength(255)]
    public string? Domain { get; set; }

    [ForeignKey("MessageId")]
    [InverseProperty("ChatWebSources")]
    public virtual ChatMessage? Message { get; set; }
}
