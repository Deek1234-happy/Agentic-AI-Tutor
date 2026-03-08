using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class ChatSessionRequest
    {
        [Required]
        public Guid UserId { get; set; }
        public List<Guid> DocumentIds { get; set; } = new List<Guid>();
    }
}
