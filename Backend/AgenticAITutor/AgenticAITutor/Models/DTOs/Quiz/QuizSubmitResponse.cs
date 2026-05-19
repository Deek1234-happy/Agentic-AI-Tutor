namespace AgenticAITutor.Models.DTOs
{
    public class QuizSubmitResponse
    {
        public Guid AttemptId { get; set; }
        public double Score { get; set; }
        public int CorrectCount { get; set; }
        public int TotalCount { get; set; }
        public DateTime FinishedAt { get; set; }
    }
}
