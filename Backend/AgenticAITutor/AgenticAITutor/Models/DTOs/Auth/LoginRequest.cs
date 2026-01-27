using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs.Auth
{
    public class LoginRequest
    {
        public string? Email { get; set; }
        public string? Password { get; set; }
    }
}
