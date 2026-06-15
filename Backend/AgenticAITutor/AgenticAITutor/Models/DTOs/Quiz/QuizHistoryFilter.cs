namespace AgenticAITutor.Models.DTOs
{
    public class QuizHistoryFilter
    {
        public Guid? SubjectId { get; set; }
        public string? Status { get; set; }
        public int Page { get; set; } = 1;
        public int PageSize { get; set; } = 10;
    }
}
