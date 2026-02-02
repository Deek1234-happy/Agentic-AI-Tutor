using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("document_chunks", Schema = "content")]
public partial class DocumentChunk
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("document_id")]
    public Guid? DocumentId { get; set; }

    [Column("chunk_text")]
    public string ChunkText { get; set; } = null!;

    [Column("topic")]
    [StringLength(255)]
    public string? Topic { get; set; }

    [Column("difficulty")]
    [StringLength(50)]
    public string? Difficulty { get; set; }

    [Column("token_count")]
    public int? TokenCount { get; set; }

    [Column("page_start")]
    public int? PageStart { get; set; }

    [Column("page_end")]
    public int? PageEnd { get; set; }

    [Column("created_at", TypeName = "timestamp without time zone")]
    public DateTime? CreatedAt { get; set; }

    [ForeignKey("DocumentId")]
    [InverseProperty("DocumentChunks")]
    public virtual Document? Document { get; set; }

    [ForeignKey("ChunkId")]
    [InverseProperty("Chunks")]
    public virtual ICollection<ChatMessage> Messages { get; set; } = new List<ChatMessage>();

    [ForeignKey("ChunkId")]
    [InverseProperty("Chunks")]
    public virtual ICollection<QuizQuestion> Questions { get; set; } = new List<QuizQuestion>();
}
