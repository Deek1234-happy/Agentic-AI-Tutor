using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

public partial class activity_log
{
    [Key]
    public Guid id { get; set; }

    public Guid? user_id { get; set; }

    [StringLength(255)]
    public string? action { get; set; }

    [Column(TypeName = "jsonb")]
    public string? metadata { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? timestamp { get; set; }

    [ForeignKey("user_id")]
    [InverseProperty("activity_logs")]
    public virtual user? user { get; set; }
}
