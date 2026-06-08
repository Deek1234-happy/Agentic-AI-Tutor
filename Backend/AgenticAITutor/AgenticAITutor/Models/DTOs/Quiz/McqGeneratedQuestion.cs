using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqGeneratedQuestion
    {
        [JsonPropertyName("question_text")]
        public string QuestionText { get; set; } = string.Empty;

        [JsonPropertyName("options")]
        public List<McqGeneratedOption> Options { get; set; } = new();
        [JsonPropertyName("correct_option")]
        public char CorrectOption { get; set; }

        [JsonPropertyName("explanation")]
        public string? Explanation { get; set; }

        [JsonPropertyName("concept")]
        public string? Concept { get; set; }

        [JsonPropertyName("bloom_level")]
        public string? BloomLevel { get; set; }

        /// <summary>Primary source chunk that generated this question.</summary>
        [JsonPropertyName("chunk_id")]
        public Guid? ChunkId { get; set; }

    }
}
