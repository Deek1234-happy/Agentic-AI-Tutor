using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("quiz_questions", Schema = "quiz")]
[Index("QuizId", "SlotIndex", Name = "idx_quiz_questions_quiz_slot")]
public partial class QuizQuestion
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("quiz_id")]
    public Guid? QuizId { get; set; }

    [Column("question_text")]
    public string QuestionText { get; set; } = null!;

    [Column("correct_option")]
    [MaxLength(1)]
    public char CorrectOption { get; set; }

    [Column("explanation")]
    public string? Explanation { get; set; }

    [Column("concept")]
    [StringLength(255)]
    public string? Concept { get; set; }

    [Column("bloom_level")]
    [StringLength(50)]
    public string? BloomLevel { get; set; }

    [Column("slot_index")]
    public int? SlotIndex { get; set; }

    [Column("chunk_id")]
    public Guid? ChunkId { get; set; }

    [ForeignKey("ChunkId")]
    [InverseProperty("QuizQuestions")]
    public virtual QuizChunk? Chunk { get; set; }

    [ForeignKey("QuizId")]
    [InverseProperty("QuizQuestions")]
    public virtual Quiz? Quiz { get; set; }

    [InverseProperty("Question")]
    public virtual ICollection<QuizAnswer> QuizAnswers { get; set; } = new List<QuizAnswer>();

    [InverseProperty("Question")]
    public virtual ICollection<QuizOption> QuizOptions { get; set; } = new List<QuizOption>();
}
