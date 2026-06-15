using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class STTResponse
    {
        [JsonPropertyName("text")]
        public string? Text { get; set; }
    }
}
