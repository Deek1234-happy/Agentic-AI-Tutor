using System.ComponentModel.DataAnnotations;

namespace AgenticAITutorDeom.Models.DTOs.Auth
{
    public class RegisterRequest
    {
        [Required, StringLength(100)]
        public string? FirstName {  get; set; }
        [Required, StringLength(100)]
        public string? LastName { get; set; }
        [Required, StringLength(100)]
        public string? Email { get; set; }
        [Required, StringLength(30)]
        public string? Password { get; set; }
    }
}
