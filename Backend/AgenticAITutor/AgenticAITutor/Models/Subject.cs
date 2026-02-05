using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("subjects", Schema = "content")]
[Index("UserId", "Name", Name = "unique_subject_per_user", IsUnique = true)]
public partial class Subject
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("name")]
    [StringLength(255)]
    public string Name { get; set; } = null!;

    [Column("user_id")]
    public Guid UserId { get; set; }

    [InverseProperty("Subject")]
    public virtual ICollection<Document> Documents { get; set; } = new List<Document>();

    [ForeignKey("UserId")]
    [InverseProperty("Subjects")]
    public virtual User User { get; set; } = null!;
}
