namespace AgenticAITutor.Models.DTOs
{
    public class QuizQuestionDto
    {
        public Guid Id { get; set; }
        public int SlotIndex { get; set; }
        public string QuestionText { get; set; } = string.Empty;
        public string? BloomLevel { get; set; }
        public string? Concept { get; set; }
        public List<QuizOptionDto> Options { get; set; } = new();
    }
}
