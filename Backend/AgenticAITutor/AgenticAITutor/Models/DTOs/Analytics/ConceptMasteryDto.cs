namespace AgenticAITutor.Models.DTOs.Analytics;

public class ConceptMasteryDto
{
    public string ConceptName { get; set; } = string.Empty;
    public int ErrorCount { get; set; }
    public int CorrectCount { get; set; }
    public int QuestionCount { get; set; }
    public int Accuracy { get; set; }
    public Guid SubjectId { get; set; }
    public string SubjectName { get; set; } = string.Empty;
    public Guid? ReviewAttemptId { get; set; }
    public List<Guid> SourceDocumentIds { get; set; } = new();
    public List<Guid> SourceChunkIds { get; set; } = new();
}
