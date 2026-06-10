using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class DocumentRepository : IDocumentRepository
    {
        private readonly AppDbContext dbContext;

        public DocumentRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }
        public async Task AddAsync(Document document)
        {
            await dbContext.Documents.AddAsync(document);
            await dbContext.SaveChangesAsync();
        }
        public async Task UpdateAsync(Document document)
        {
            dbContext.Documents.Update(document);
            await dbContext.SaveChangesAsync();
        }
        public async Task DeleteAsync(Document document)
        {
            dbContext.Documents.Remove(document);
            await dbContext.SaveChangesAsync();
        }

        public async Task<List<Document>> GetAllAsync(Guid userId)
        {
            return await dbContext.Documents.Where(d => d.UserId == userId).ToListAsync();
            
        }

        public async Task<Document?> GetByHashAsync(string contentHash, Guid userId)
        {
            return await dbContext.Documents.FirstOrDefaultAsync(d => d.UserId == userId && d.ContentHash == contentHash);
        }

        public async Task<Document?> GetByIdAsync(Guid id)
        {
            return await dbContext.Documents.FirstOrDefaultAsync(d => d.Id == id);
        }

        public async Task<List<Document>> GetBySubjectAsync(Guid userId, Guid subjectId)
        {
            return await dbContext.Documents.Where(d => d.UserId == userId && d.SubjectId == subjectId).ToListAsync();
        }

        public async Task<List<Document>> GetDocumentsByIdsAsync(List<Guid> documentIds, Guid userId)
        {
            return await dbContext.Documents
                .Where(d => documentIds.Contains(d.Id) && d.UserId == userId)
                .ToListAsync();
        }

    }
}
