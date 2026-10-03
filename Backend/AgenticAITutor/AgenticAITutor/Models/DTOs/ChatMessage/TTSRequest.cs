using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class TTSRequest
    {
        [JsonPropertyName("text")]
        public string? Text { get; set; }
        [JsonPropertyName("language")]
        public string Language { get; set; } = "en";
    }
}
