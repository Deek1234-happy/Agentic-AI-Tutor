using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class DocumentRequest
    {
        [Required]
        public Guid UserId { get; set; }
        [Required]
        public IFormFile? File { get; set; }
        public Guid? SubjectId { get; set; } // User Can Upload Documents That is not Related to a Subject
    }
}
