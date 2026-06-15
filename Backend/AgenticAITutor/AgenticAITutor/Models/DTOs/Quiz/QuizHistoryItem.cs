namespace AgenticAITutor.Models.DTOs
{
    public class QuizHistoryItem
    {
        public Guid QuizId { get; set; }
        public string Status { get; set; } = string.Empty;
        public Guid? SubjectId { get; set; }
        public string? SubjectName { get; set; }
        public int QuestionCount { get; set; }
        public DateTime? CreatedAt { get; set; }
        public int AttemptCount { get; set; }
        public double? BestScore { get; set; }
    }
}
