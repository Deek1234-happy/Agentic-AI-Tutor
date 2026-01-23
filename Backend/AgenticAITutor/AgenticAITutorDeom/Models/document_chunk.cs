using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Models;

[Table("document_chunks", Schema = "content")]
public partial class document_chunk
{
    [Key]
    public Guid id { get; set; }

    public Guid? document_id { get; set; }

    public string chunk_text { get; set; } = null!;

    [StringLength(255)]
    public string? topic { get; set; }

    [StringLength(50)]
    public string? difficulty { get; set; }

    public int? token_count { get; set; }

    public int? page_start { get; set; }

    public int? page_end { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? created_at { get; set; }

    [ForeignKey("document_id")]
    [InverseProperty("document_chunks")]
    public virtual document? document { get; set; }

    [ForeignKey("chunk_id")]
    [InverseProperty("chunks")]
    public virtual ICollection<chat_message> messages { get; set; } = new List<chat_message>();

    [ForeignKey("chunk_id")]
    [InverseProperty("chunks")]
    public virtual ICollection<quiz_question> questions { get; set; } = new List<quiz_question>();
}
