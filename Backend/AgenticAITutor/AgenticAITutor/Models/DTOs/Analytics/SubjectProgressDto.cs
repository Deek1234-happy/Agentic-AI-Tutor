namespace AgenticAITutor.Models.DTOs.Analytics;

public class SubjectProgressDto
{
    public string Subject { get; set; } = string.Empty;
    public int Mastery { get; set; }
    public int Quizzes { get; set; }
    public string StudyTime { get; set; } = string.Empty;
}
