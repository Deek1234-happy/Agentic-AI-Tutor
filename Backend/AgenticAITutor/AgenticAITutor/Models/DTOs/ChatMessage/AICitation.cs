using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class AICitation
    {
        [JsonPropertyName("document_id")]
        public Guid? DocumentId { get; set; }
        [JsonPropertyName("chunk_id")]
        public Guid ChunkId { get; set; }
        [JsonPropertyName("page_start")]
        public int PageStart { get; set; }
        [JsonPropertyName("page_end")]
        public int PageEnd { get; set; }
    }
}
