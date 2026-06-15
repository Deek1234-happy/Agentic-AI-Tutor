using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class QuizAnswerItem
    {
        [Required]
        public Guid QuestionId { get; set; }

        [Required]
        public char SelectedOption { get; set; }
    }
}
