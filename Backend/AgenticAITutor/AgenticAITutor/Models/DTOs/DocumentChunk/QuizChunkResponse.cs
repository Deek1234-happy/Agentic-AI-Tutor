using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class QuizChunkResponse
    {
        [JsonPropertyName("chunk_index")]
        public int ChunkIndex { get; set; }
        [JsonPropertyName("text")]
        public string ChunkText { get; set; }
        [JsonPropertyName("context_prev_sentence")]
        public string? ContextPrevSentence { get; set; }
        [JsonPropertyName("context_next_sentence")]
        public string? ContextNextSentence { get; set; }
        [JsonPropertyName("semantic_score")]
        public double? SemanticScore { get; set; }
        [JsonPropertyName("quality_score")]
        public double? QualityScore { get; set; }
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
