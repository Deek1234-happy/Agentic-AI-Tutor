using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Models;

[Table("study_plans", Schema = "planner")]
public partial class study_plan
{
    [Key]
    public Guid id { get; set; }

    public Guid? user_id { get; set; }

    public DateOnly start_date { get; set; }

    public DateOnly end_date { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? created_at { get; set; }

    [InverseProperty("plan")]
    public virtual ICollection<study_plan_item> study_plan_items { get; set; } = new List<study_plan_item>();

    [ForeignKey("user_id")]
    [InverseProperty("study_plans")]
    public virtual user? user { get; set; }

    [ForeignKey("plan_id")]
    [InverseProperty("plans")]
    public virtual ICollection<document> documents { get; set; } = new List<document>();
}
