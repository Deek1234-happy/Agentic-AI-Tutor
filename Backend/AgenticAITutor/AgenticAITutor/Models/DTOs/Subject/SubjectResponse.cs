namespace AgenticAITutor.Models.DTOs
{
    public class SubjectResponse
    {
        public Guid Id { get; set; }
        public string Name { get; set; }
        public Guid UserId { get; set; }
        public List<DocumentResponse> Documents { get ; set; } = new List<DocumentResponse>();
    }
}
