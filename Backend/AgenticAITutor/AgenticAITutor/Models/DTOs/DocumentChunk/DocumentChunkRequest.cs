namespace AgenticAITutor.Models.DTOs
{
    public class DocumentChunkRequest
    {
        public Guid Id { get; set; }
        public Guid DocumentId {  get; set; }
        public Guid UserId { get; set; }
        public Guid? SubjectId { get; set; }
        public string? DocumentPath { get; set; }
    }
}
