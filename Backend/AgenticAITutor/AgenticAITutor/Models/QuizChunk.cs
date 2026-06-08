using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quiz_chunks", Schema = "content")]
public partial class QuizChunk
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("document_id")]
    public Guid? DocumentId { get; set; }

    [Column("chunk_index")]
    public int ChunkIndex { get; set; }

    [Column("chunk_text")]
    public string ChunkText { get; set; } = null!;

    [Column("context_prev_sentence")]
    public string? ContextPrevSentence { get; set; }

    [Column("context_next_sentence")]
    public string? ContextNextSentence { get; set; }

    [Column("semantic_score")]
    public double? SemanticScore { get; set; }

    [Column("quality_score")]
    public double? QualityScore { get; set; }

    [Column("bloom_level")]
    [StringLength(50)]
    public string? BloomLevel { get; set; }

    [Column("chunk_type")]
    [StringLength(50)]
    public string? ChunkType { get; set; }

    [Column("concepts")]
    public List<string>? Concepts { get; set; }

    [Column("keywords")]
    public List<string>? Keywords { get; set; }

    [Column("created_at", TypeName = "timestamp without time zone")]
    public DateTime? CreatedAt { get; set; }

    [Column("subject_id")]
    public Guid? SubjectId { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [ForeignKey("DocumentId")]
    [InverseProperty("QuizChunks")]
    public virtual Document? Document { get; set; }

    [InverseProperty("Chunk")]
    public virtual ICollection<QuizQuestion> QuizQuestions { get; set; } = new List<QuizQuestion>();

    [ForeignKey("SubjectId")]
    [InverseProperty("QuizChunks")]
    public virtual Subject? Subject { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("QuizChunks")]
    public virtual User? User { get; set; }
}
