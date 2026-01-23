namespace AgenticAITutorDeom.Models.DTOs.Auth
{
    public class AuthResponse
    {
        public Guid UserId { get; set; }
        public string? Email { get; set; }
        public string? Token { get; set; }
        public DateTime ExpiresIn { get; set; }
        public string? Message {  get; set; }
        public bool IsAuthenticated { get; set; }

    }
}
