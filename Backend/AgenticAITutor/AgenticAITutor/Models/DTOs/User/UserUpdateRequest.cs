using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class UserUpdateRequest
    {
        public string? FirstName { get; set; }
        public string? LastName { get; set; }

        [EmailAddress]
        public string? Email { get; set; }
    }
}
