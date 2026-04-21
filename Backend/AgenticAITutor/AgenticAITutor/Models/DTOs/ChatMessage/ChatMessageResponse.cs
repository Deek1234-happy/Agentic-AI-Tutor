using System.ComponentModel.DataAnnotations.Schema;
using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs
{
    public class ChatMessageResponse
    {
        public Guid Id { get; set; }
        public Guid SessionId { get; set; }
        public string Role { get; set; }
        public string Content { get; set; }
        public double? ConfidenceScore { get; set; }
        public DateTime? CreatedAt { get; set; }
        public string? AudioUrl { get; set; }
        public virtual List<WebSources> WebSource { get; set; } = new List<WebSources>();
        public virtual List<AICitation> AICitation { get; set; } = new List<AICitation>();
        public KgContextData? KgContext { get; set; }

    }
}
