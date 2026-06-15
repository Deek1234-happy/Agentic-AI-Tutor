namespace AgenticAITutor.Models.DTOs
{
    public class QuizStatusResponse
    {
        public Guid QuizId { get; set; }
        public string Status { get; set; } = string.Empty;
        public int QuestionCount { get; set; }
        public DateTime? GeneratedAt { get; set; }
    }
}
