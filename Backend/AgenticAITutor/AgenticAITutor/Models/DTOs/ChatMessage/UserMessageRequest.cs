namespace AgenticAITutor.Models.DTOs
{
    public class UserMessageRequest
    {
        public string? UserMessage { get; set; }
        public Guid UserId { get; set; }
        public Guid SessionId { get; set; }
        public List<Guid>? AllowedDocumentIds { get; set; } = new List<Guid>();
    }
}
