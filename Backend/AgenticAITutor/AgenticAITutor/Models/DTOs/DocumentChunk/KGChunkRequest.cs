using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class KGChunkRequest
    {
        [JsonPropertyName("file_id")]
        public Guid DocumentId { get; set; }
    }
}
