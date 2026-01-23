using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("study_plan_items", Schema = "planner")]
public partial class study_plan_item
{
    [Key]
    public Guid id { get; set; }

    public Guid? plan_id { get; set; }

    [StringLength(255)]
    public string concept_ref { get; set; } = null!;

    public int? estimated_time { get; set; }

    public DateOnly? scheduled_date { get; set; }

    public bool? completed { get; set; }

    [ForeignKey("plan_id")]
    [InverseProperty("study_plan_items")]
    public virtual study_plan? plan { get; set; }
}
