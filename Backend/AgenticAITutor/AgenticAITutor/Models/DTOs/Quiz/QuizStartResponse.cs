namespace AgenticAITutor.Models.DTOs
{
    public class QuizStartResponse
    {
        public Guid QuizId { get; set; }
        public Guid AttemptId { get; set; }
        public int AttemptNumber { get; set; }
        public List<QuizQuestionDto> Questions { get; set; } = new();
    }
}
