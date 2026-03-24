using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class WebSearchResponse
    {
        [JsonPropertyName("answer")]
        public string Answer { get; set; } = string.Empty;
        [JsonPropertyName("sources")]
        public List<WebSources> Sources { get; set; } = new List<WebSources>();
    }
}
