using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqGenerateResponse
    {
        [JsonPropertyName("questions")]
        public List<McqGeneratedQuestion> Questions { get; set; } = new();
    }
}
