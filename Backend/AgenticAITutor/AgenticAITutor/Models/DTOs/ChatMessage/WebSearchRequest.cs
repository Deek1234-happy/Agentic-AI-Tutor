using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class WebSearchRequest
    {
        [JsonPropertyName("session_id")]
        [Required]
        public Guid SessionId { get; set; }
        [JsonPropertyName("question")]
        [Required]
        public string Question { get; set; } = string.Empty;
        [JsonPropertyName("language")]
        [Required]
        [RegularExpression("^(en|kn|hi|ml|ta|te)$", ErrorMessage = "Unsupported language.")]
        public string Language { get; set; } = "en";
    }
}
