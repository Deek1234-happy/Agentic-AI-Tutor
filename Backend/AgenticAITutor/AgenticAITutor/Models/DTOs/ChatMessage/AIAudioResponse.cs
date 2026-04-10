using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs.ChatMessage
{
    public class AIAudioResponse
    {
        [JsonPropertyName("transcription")]
        public string? Transcription { get; set; }

        [JsonPropertyName("answer_text")]
        public string? AnswerText { get; set; }

        [JsonPropertyName("audio_url")]
        public string? AudioUrl { get; set; }

        [JsonPropertyName("confidence")]
        public double Confidence { get; set; }

        [JsonPropertyName("citations")]
        public List<AICitation>? Citations { get; set; } = new List<AICitation>();
    }
}
