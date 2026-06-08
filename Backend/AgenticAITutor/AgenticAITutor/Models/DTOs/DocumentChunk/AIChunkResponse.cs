using Pgvector;
using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class AIChunkResponse
    {
        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;
        [JsonPropertyName("page_start")]
        public int? PageStart { get; set; }
        [JsonPropertyName("page_end")]
        public int? PageEnd { get; set; }
        [JsonPropertyName("embedding")]
        public float[] Embedding { get; set; } = Array.Empty<float>();
    }
}
