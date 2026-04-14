using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace AgenticAITutor.Models.DTOs
{
    public class SubjectRequest
    {
        [Required]
        [StringLength(255)]
        public string Name { get; set; }
        [JsonIgnore]
        [Required]
        public Guid UserId { get; set; }
    }
}
