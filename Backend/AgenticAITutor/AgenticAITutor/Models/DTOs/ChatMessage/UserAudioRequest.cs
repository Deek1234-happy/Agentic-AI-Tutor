using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs.ChatMessage
{
    public class UserAudioRequest
    {
        [JsonPropertyName("user_id")]
        public Guid UserId { get; set; }
        [JsonPropertyName("session_id")]
        public Guid SessionId { get; set; }
        [JsonPropertyName("audio")]
        public IFormFile Audio {  get; set; }
    }
}
