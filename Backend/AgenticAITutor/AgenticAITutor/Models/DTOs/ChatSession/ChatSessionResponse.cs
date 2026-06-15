namespace AgenticAITutor.Models.DTOs
{
    public class ChatSessionResponse
    {
        public Guid Id { get; set; }
        public string Title { get; set; }
        public DateTime? StartedAt { get; set; }
        public DateTime? UpdatedAt { get; set; }
        public int NumberOfDocuments { get; set; }
        public List<DocumentResponse> Documents { get; set; }
    }
}
