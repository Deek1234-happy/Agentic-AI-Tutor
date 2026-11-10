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
        [Required]
        [Range(1, int.MaxValue, ErrorMessage = "Number of questions must be at least 1.")]
        public int NumberOfQuestions { get; set; }

        [StringLength(255)]
        public string? FocusConcept { get; set; }

        public List<Guid> SourceChunkIds { get; set; } = new();
    }
}
