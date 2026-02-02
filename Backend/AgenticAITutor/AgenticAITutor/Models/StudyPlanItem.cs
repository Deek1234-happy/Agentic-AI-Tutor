using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("study_plan_items", Schema = "planner")]
public partial class StudyPlanItem
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("plan_id")]
    public Guid? PlanId { get; set; }

    [Column("concept_ref")]
    [StringLength(255)]
    public string ConceptRef { get; set; } = null!;

    [Column("estimated_time")]
    public int? EstimatedTime { get; set; }

    [Column("scheduled_date")]
    public DateOnly? ScheduledDate { get; set; }

    [Column("completed")]
    public bool? Completed { get; set; }

    [ForeignKey("PlanId")]
    [InverseProperty("StudyPlanItems")]
    public virtual StudyPlan? Plan { get; set; }
}
