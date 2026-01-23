using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("documents", Schema = "content")]
[Index("user_id", "content_hash", Name = "documents_user_id_content_hash_key", IsUnique = true)]
public partial class document
{
    [Key]
    public Guid id { get; set; }

    public Guid? user_id { get; set; }

    [StringLength(255)]
    public string filename { get; set; } = null!;

    [StringLength(50)]
    public string file_type { get; set; } = null!;

    public int? file_size { get; set; }

    public string storage_path { get; set; } = null!;

    [StringLength(64)]
    public string content_hash { get; set; } = null!;

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? upload_time { get; set; }

    public bool? is_deleted { get; set; }

    [InverseProperty("document")]
    public virtual ICollection<document_chunk> document_chunks { get; set; } = new List<document_chunk>();

    [ForeignKey("user_id")]
    [InverseProperty("documents")]
    public virtual user? user { get; set; }

    [ForeignKey("document_id")]
    [InverseProperty("documents")]
    public virtual ICollection<study_plan> plans { get; set; } = new List<study_plan>();
}
