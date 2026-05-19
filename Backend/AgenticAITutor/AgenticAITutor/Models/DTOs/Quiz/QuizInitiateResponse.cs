namespace AgenticAITutor.Models.DTOs
{
    public class QuizInitiateResponse
    {
        public Guid QuizId { get; set; }
        public string Status { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
    }
}
