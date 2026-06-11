using System.Collections.Generic;

namespace AgenticAITutor.Models.DTOs.Analytics;

public class ProgressDashboardResponseDto
{
    public int TotalQuizzes { get; set; }
    public int ActiveSubjects { get; set; }
    public int OverallMastery { get; set; }

    public List<MonthlyPerformanceDto> MonthlyPerformance { get; set; } = new();
    public List<SubjectProgressDto> SubjectProgress { get; set; } = new();
    public List<ConceptMasteryDto> WeakConcepts { get; set; } = new();
}
