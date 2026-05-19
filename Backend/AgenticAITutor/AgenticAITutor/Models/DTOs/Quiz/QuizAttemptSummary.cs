namespace AgenticAITutor.Models.DTOs
{
    public class QuizAttemptSummary
    {
        public Guid AttemptId { get; set; }
        public int AttemptNumber { get; set; }
        public double? Score { get; set; }
        public DateTime? StartedAt { get; set; }
        public DateTime? FinishedAt { get; set; }
    }
}
