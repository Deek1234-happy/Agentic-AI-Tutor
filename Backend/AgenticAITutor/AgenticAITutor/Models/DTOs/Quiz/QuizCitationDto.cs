namespace AgenticAITutor.Models.DTOs
{
    public class QuizCitationDto
    {
        public Guid ChunkId { get; set; }
        public string? ChunkText { get; set; }
        public int? PageStart { get; set; }
        public int? PageEnd { get; set; }
    }
}
