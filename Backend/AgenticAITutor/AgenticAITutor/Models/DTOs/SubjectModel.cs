using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class SubjectModel
    {
        [Required]
        [StringLength(255)]
        public string Name { get; set; }
        [Required]
        public Guid UserId { get; set; }
    }
}
