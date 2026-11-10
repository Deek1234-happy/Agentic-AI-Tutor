namespace AgenticAITutor.Models.DTOs.StudyPlan;

public class ReviewScheduleItemDto
{
    public Guid Id { get; set; }
    public Guid SubjectId { get; set; }
    public string SubjectName { get; set; } = string.Empty;
    public string ConceptName { get; set; } = string.Empty;
    public DateOnly? ScheduledDate { get; set; }
    public int EstimatedMinutes { get; set; }
    public int? Accuracy { get; set; }
    public string Status { get; set; } = "Needs review";
    public bool Completed { get; set; }
}
