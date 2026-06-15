using Pgvector;
using System.ComponentModel.DataAnnotations.Schema;

namespace AgenticAITutor.Models
{
    public partial class DocumentChunk
    {
        [Column("embedding",TypeName = "vector(768)")]
        public Vector? Embedding { get; set; }
    }
}
