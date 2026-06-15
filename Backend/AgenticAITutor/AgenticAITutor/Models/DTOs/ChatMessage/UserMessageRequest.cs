using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class UserMessageRequest
    {
        [JsonPropertyName("question")]
        [Required]
        public string? UserMessage { get; set; }
        [JsonPropertyName("user_id")]
        [Required]
        public Guid UserId { get; set; }
        [JsonPropertyName("session_id")]
        [Required]
        public Guid SessionId { get; set; }
        [JsonPropertyName("allowed_document_ids")]
        public List<Guid>? AllowedDocumentIds { get; set; } = new List<Guid>();
        [Required]
        public bool SearchWeb { get; set; } = false;
    }
}
