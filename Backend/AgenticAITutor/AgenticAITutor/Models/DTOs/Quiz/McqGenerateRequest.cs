using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqGenerateRequest
    {
        [JsonPropertyName("chunks")]
        public List<McqChunkInput> Chunks { get; set; } = new();
    }
}
