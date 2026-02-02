using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("documents", Schema = "content")]
[Index("UserId", "ContentHash", Name = "documents_user_id_content_hash_key", IsUnique = true)]
public partial class Document
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("user_id")]
    public Guid UserId { get; set; }

    [Column("filename")]
    [StringLength(255)]
    public string Filename { get; set; } = null!;

    [Column("file_type")]
    [StringLength(50)]
    public string FileType { get; set; } = null!;

    [Column("file_size")]
    public int? FileSize { get; set; }

    [Column("storage_path")]
    public string StoragePath { get; set; } = null!;

    [Column("content_hash")]
    [StringLength(64)]
    public string ContentHash { get; set; } = null!;

    [Column("upload_time", TypeName = "timestamp without time zone")]
    public DateTime? UploadTime { get; set; }

    [Column("is_deleted")]
    public bool? IsDeleted { get; set; }

    [Column("subject_id")]
    public Guid? SubjectId { get; set; }

    [InverseProperty("Document")]
    public virtual ICollection<DocumentChunk> DocumentChunks { get; set; } = new List<DocumentChunk>();

    [ForeignKey("SubjectId")]
    [InverseProperty("Documents")]
    public virtual Subject? Subject { get; set; }

    [ForeignKey("UserId")]
    [InverseProperty("Documents")]
    public virtual User User { get; set; } = null!;

    [ForeignKey("DocumentId")]
    [InverseProperty("Documents")]
    public virtual ICollection<StudyPlan> Plans { get; set; } = new List<StudyPlan>();
}
