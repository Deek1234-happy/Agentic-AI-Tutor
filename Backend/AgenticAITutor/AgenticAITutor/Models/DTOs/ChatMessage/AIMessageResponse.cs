using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
    {
        public class AIMessageResponse
        {
            [JsonPropertyName("answer")]
            public string? AIMessage { get; set; }

        [JsonPropertyName("confidence_score")]
        public double ConfidenceScore { get; set; } = 0;
        [JsonPropertyName("citations")]
            public List<AICitationDTO>? UsedChunks { get; set; }
        }
    }
