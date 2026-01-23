using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

public partial class notification
{
    [Key]
    public Guid id { get; set; }

    public Guid? user_id { get; set; }

    [StringLength(255)]
    public string? title { get; set; }

    public string? message { get; set; }

    [StringLength(50)]
    public string? type { get; set; }

    public bool? is_read { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? created_at { get; set; }

    [ForeignKey("user_id")]
    [InverseProperty("notifications")]
    public virtual user? user { get; set; }
}
