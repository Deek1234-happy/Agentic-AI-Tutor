using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class AIChunkRequest
    {
        [JsonPropertyName("file_path")]
        public string DocumentPath { get; set; } = string.Empty;
        [JsonPropertyName("file_type")]
        public string DocumentType { get; set; } = string.Empty;
    }
}
