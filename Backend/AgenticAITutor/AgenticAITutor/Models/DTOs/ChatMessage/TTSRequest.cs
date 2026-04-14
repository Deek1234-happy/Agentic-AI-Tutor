using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class TTSRequest
    {
        [JsonPropertyName("text")]
        public string? Text { get; set; }
    }
}
