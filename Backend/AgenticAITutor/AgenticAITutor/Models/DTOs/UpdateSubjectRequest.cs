using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class UpdateSubjectRequest
    {
        [Required]
        public string OldName { get; set; }
        [Required]
        public string NewName { get; set; }
    }
}
