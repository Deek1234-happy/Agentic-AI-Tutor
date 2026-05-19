using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqChunkInput
    {
        [JsonPropertyName("chunk_id")]
        public Guid ChunkId { get; set; }

        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;

        [JsonPropertyName("bloom_level")]
        public string? BloomLevel { get; set; }

        [JsonPropertyName("chunk_type")]
        public string? ChunkType { get; set; }

        [JsonPropertyName("concepts")]
        public List<string>? Concepts { get; set; }

        [JsonPropertyName("keywords")]
        public List<string>? Keywords { get; set; }
    }
}
