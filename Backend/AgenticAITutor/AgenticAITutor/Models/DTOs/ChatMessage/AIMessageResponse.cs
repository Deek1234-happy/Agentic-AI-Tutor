namespace AgenticAITutor.Models.DTOs
{
    public class AIMessageResponse
    {
        public string? AIMessage { get; set; }
        public List<AICitationDTO>? UsedChunks { get; set; }
    }
}
