using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class WebSources
    {
        [JsonPropertyName("title")]
        public string Title { get; set; } = string.Empty;
        [JsonPropertyName("url")]
        public string URL { get; set; } = string.Empty;
        [JsonPropertyName("domain")]
        public string Domain { get; set; } = string.Empty ;
    }
}
