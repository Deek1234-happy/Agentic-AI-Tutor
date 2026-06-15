using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class ChatSessionUpdate
    {
        [Required]
        public Guid SessionId { get; set; }
        [Required]
        public Guid UserId { get; set; }
        [Required]
        [MaxLength(255)]
        public string Title { get; set; } = string.Empty;
    }
}
