using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqGeneratedOption
    {
        [JsonPropertyName("label")]
        public char Label { get; set; }

        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;
    }
}
