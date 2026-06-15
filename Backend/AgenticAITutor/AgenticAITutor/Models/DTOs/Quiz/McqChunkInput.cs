using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqChunkInput
    {
        [JsonPropertyName("chunk_id")]
        public Guid ChunkId { get; set; }
        [JsonPropertyName("document_id")]
        public Guid? DocumentId { get; set; }
        [JsonPropertyName("chunk_text")]
        public string ChunkText { get; set; }
        [JsonPropertyName("context_prev_sentence")]
        public string? ContextPrevSentence { get; set; }
        [JsonPropertyName("context_next_sentence")]
        public string? ContextNextSentence { get; set; }
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
