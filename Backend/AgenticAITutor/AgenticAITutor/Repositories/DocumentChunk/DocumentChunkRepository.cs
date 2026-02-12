using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class DocumentChunkRepository : IDocumentChunkRepository
    {
        private readonly AppDbContext dbContext;

        public DocumentChunkRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task AddAsync(DocumentChunk chunk)
        {
            await dbContext.DocumentChunks.AddAsync(chunk);
            await dbContext.SaveChangesAsync();
        }
        public async Task AddRangeAsync(List<DocumentChunk> chunks)
        {
            await dbContext.DocumentChunks.AddRangeAsync(chunks);
            await dbContext.SaveChangesAsync();
        }
        public async Task UpdateAsync(DocumentChunk chunk)
        {
            dbContext.DocumentChunks.Update(chunk);
            await dbContext.SaveChangesAsync();
        }

        public async Task DeleteAsync(DocumentChunk chunk)
        {
            dbContext.DocumentChunks.Remove(chunk);
            await dbContext.SaveChangesAsync();
        }

        public async Task<List<DocumentChunk>> GetAllAsync(Guid userId)
        {
            return await dbContext.DocumentChunks.Where(c => c.UserId == userId).ToListAsync();
        }
        public async Task<DocumentChunk?> GetByIdAsync(Guid id)
        {
            return await dbContext.DocumentChunks.FirstOrDefaultAsync(c => c.Id == id);
        }

        public async Task<List<DocumentChunk>> GetByDocumentAsync(Guid documentId, Guid userId)
        {
            return await dbContext.DocumentChunks.Where(c => c.UserId == userId && c.DocumentId == documentId).ToListAsync();
        }

        public async Task<List<DocumentChunk>> GetBySubjectAsync(Guid subjectId, Guid userId)
        {
            return await dbContext.DocumentChunks.Where(c => c.UserId == userId && c.SubjectId == subjectId).ToListAsync();
        }
    }
}
