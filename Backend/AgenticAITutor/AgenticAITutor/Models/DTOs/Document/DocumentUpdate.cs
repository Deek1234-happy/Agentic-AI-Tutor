using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class DocumentUpdate
    {
        [Required]
        public Guid Id { get; set; }
        [Required]
        public Guid UserId { get; set; }
        public string? NewName { get; set; }
        public Guid? NewSubjectId { get; set; }
        public bool MoveToGeneral { get; set; } = false;
    }
}
