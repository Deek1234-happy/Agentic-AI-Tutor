namespace AgenticAITutor.Models.DTOs
{
    public class QuizReviewResponse
    {
        public Guid AttemptId { get; set; }
        public Guid QuizId { get; set; }
        public double Score { get; set; }
        public int CorrectCount { get; set; }
        public int TotalCount { get; set; }
        public DateTime? StartedAt { get; set; }
        public DateTime? FinishedAt { get; set; }
        public List<QuizReviewQuestionDto> Questions { get; set; } = new();
    }
}
