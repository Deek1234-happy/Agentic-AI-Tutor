using Pgvector;

namespace AgenticAITutor.Models.DTOs
{
    public class DocumentChunkResponse
    {
        public Guid Id { get; set; }
        public string Text { get; set; } = string.Empty;
        public int PageStart { get; set; }
        public int PageEnd { get; set; }
        public Vector? Embedding { get; set; }
    }
}

