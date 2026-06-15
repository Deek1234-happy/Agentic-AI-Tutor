using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class KgContextData
    {
        [JsonPropertyName("entities")]
        public List<KgEntity> Entities { get; set; } = new();

        [JsonPropertyName("relationships")]
        public List<KgRelation> Relationships { get; set; } = new();
    }
    public class KgEntity
    {
        [JsonPropertyName("id")]
        public string Id { get; set; }
        [JsonPropertyName("label")]
        public string Label { get; set; }
        [JsonPropertyName("type")]
        public string Type { get; set; }
    }
    public class KgRelation
    {
        [JsonPropertyName("source")]
        public string Source { get; set; }
        [JsonPropertyName("relation")]
        public string Relation { get; set; }
        [JsonPropertyName("target")]
        public string Target { get; set; }
    }
}
