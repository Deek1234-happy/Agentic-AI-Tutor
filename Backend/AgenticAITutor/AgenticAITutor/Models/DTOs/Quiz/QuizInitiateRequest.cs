using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class QuizInitiateRequest
    {
        [Required]
        public Guid SubjectId { get; set; }

        [Required]
        [MinLength(1, ErrorMessage = "At least one document is required.")]
        public List<Guid> DocumentIds { get; set; } = new();
    }
}
