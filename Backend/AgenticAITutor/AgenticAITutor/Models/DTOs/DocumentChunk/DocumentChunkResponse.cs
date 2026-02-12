using Pgvector;

namespace AgenticAITutor.Models.DTOs
{
    public class DocumentChunkResponse
    {
        public Guid Id { get; set; }
        public string Text {  get; set; } = string.Empty;
        public string? Topic { get; set; }
        public string? Difficulty { get; set; }
        public int TokenCount { get; set; }
        public int PageStart { get; set; }
        public int PageEnd { get; set; }
        public Vector? Embedding { get; set; }
    }
}
