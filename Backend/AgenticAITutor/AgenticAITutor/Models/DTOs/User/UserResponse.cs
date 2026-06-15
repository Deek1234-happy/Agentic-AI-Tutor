namespace AgenticAITutor.Models.DTOs
{
    public class UserResponse
    {
        public Guid Id { get; set; }
        public string? FirstName  { get; set; }
        public string? LastName { get; set; }
        public string? Email { get; set; }
        public DateTime? CreatedDate { get; set; }
        public int NumberOfSubjects { get; set; }
        public int NumberOfDocuments { get; set; }
        public int NumberOfQuizzes { get; set; }
    }
}
