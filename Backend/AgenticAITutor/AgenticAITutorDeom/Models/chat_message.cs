using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Models;

[Table("chat_messages", Schema = "rag")]
public partial class chat_message
{
    [Key]
    public Guid id { get; set; }

    public Guid? session_id { get; set; }

    [StringLength(20)]
    public string role { get; set; } = null!;

    public string content { get; set; } = null!;

    public double? confidence_score { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? created_at { get; set; }

    [ForeignKey("session_id")]
    [InverseProperty("chat_messages")]
    public virtual chat_session? session { get; set; }

    [ForeignKey("message_id")]
    [InverseProperty("messages")]
    public virtual ICollection<document_chunk> chunks { get; set; } = new List<document_chunk>();
}
