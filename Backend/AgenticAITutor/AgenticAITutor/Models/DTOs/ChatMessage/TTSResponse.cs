using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class TTSResponse
    {
          [JsonPropertyName("audio_url")]
          public string? AudioUrl { get; set; }
    }
}
