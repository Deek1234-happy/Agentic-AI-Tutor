using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class McqGenerateRequest
    {
        [JsonPropertyName("chunks")]
        public List<McqChunkInput> Chunks { get; set; } = new();
        [JsonPropertyName("number_of_questions")]
        public int NumberOfQuestions { get; set; }
        [JsonPropertyName("mcqs_per_chunk")]
        public int McqsPerChunk { get; set; } = 1;
    }
}
