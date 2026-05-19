namespace AgenticAITutor.Models.DTOs
{
    public class QuizReviewQuestionDto
    {
        public Guid Id { get; set; }
        public string QuestionText { get; set; } = string.Empty;
        public string? Explanation { get; set; }
        public string? BloomLevel { get; set; }
        public string? Concept { get; set; }
        /// <summary>The original (unshuffled) correct label stored in DB.</summary>
        public char CorrectOption { get; set; }
        /// <summary>The original label the student selected (after reverse-mapping).</summary>
        public char? SelectedOption { get; set; }
        public bool IsCorrect { get; set; }
        public List<QuizOptionDto> Options { get; set; } = new();
        public List<QuizCitationDto> Citations { get; set; } = new();
    }
}
