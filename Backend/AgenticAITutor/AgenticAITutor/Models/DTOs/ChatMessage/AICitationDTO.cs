namespace AgenticAITutor.Models.DTOs
{
    public class AICitationDTO
    {
        public Guid? DocumentId { get; set; }
        public Guid ChunkId { get; set; }
        public double RelevanceScore { get; set; }
    }
}
