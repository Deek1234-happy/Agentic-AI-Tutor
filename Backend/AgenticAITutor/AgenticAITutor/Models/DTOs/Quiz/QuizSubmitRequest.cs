using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class QuizSubmitRequest
    {
        [Required]
        public Guid AttemptId { get; set; }

        [Required]
        [MinLength(1, ErrorMessage = "At least one answer is required.")]
        public List<QuizAnswerItem> Answers { get; set; } = new();
    }
}
