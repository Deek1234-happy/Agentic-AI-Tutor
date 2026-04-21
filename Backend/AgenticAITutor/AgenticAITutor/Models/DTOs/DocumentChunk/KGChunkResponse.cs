using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class KGChunkResponse
    {
        [JsonPropertyName("status")]
        public string Status { get; set; }
    }
}
