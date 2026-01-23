using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs.Auth
{
    public class LoginRequest
    {
        [Required, StringLength(100)]
        public string? Email { get; set; }
        [Required, StringLength(100)]
        public string? Password { get; set; }
    }
}
