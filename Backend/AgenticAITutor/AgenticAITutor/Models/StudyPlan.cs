using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("study_plans", Schema = "planner")]
public partial class StudyPlan
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("user_id")]
    public Guid? UserId { get; set; }

    [Column("start_date")]
    public DateOnly StartDate { get; set; }

    [Column("end_date")]
    public DateOnly EndDate { get; set; }

    [Column("created_at", TypeName = "timestamp without time zone")]
    public DateTime? CreatedAt { get; set; }

    [InverseProperty("Plan")]
    public virtual ICollection<StudyPlanItem> StudyPlanItems { get; set; } = new List<StudyPlanItem>();

    [ForeignKey("UserId")]
    [InverseProperty("StudyPlans")]
    public virtual User? User { get; set; }

    [ForeignKey("PlanId")]
    [InverseProperty("Plans")]
    public virtual ICollection<Document> Documents { get; set; } = new List<Document>();
}
