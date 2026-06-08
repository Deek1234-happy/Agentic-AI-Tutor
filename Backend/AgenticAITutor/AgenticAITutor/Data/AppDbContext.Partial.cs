using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Data
{
    public partial class AppDbContext
    {
        partial void OnModelCreatingPartial(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<DocumentChunk>(entity =>
            {
                entity.Property(e => e.Embedding)
                      .HasColumnType("vector(768)");
            });
        }
    }
}
