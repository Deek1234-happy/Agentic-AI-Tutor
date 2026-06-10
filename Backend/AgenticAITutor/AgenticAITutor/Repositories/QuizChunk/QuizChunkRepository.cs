using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class QuizChunkRepository: IQuizChunkRepository
    {
        private readonly AppDbContext dbContext;

        public QuizChunkRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task AddAsync(QuizChunk chunk)
        {
            await dbContext.QuizChunks.AddAsync(chunk);
            await dbContext.SaveChangesAsync();
        }
        public async Task AddRangeAsync(List<QuizChunk> chunks)
        {
            await dbContext.QuizChunks.AddRangeAsync(chunks);
            await dbContext.SaveChangesAsync();
        }
        public async Task UpdateAsync(QuizChunk chunk)
        {
            dbContext.QuizChunks.Update(chunk);
            await dbContext.SaveChangesAsync();
        }

        public async Task DeleteAsync(QuizChunk chunk)
        {
            dbContext.QuizChunks.Remove(chunk);
            await dbContext.SaveChangesAsync();
        }

        public async Task DeleteByDocumentAsync(Guid documentId)
        {
            var chunks = await dbContext.QuizChunks
                .Where(c => c.DocumentId == documentId)
                .ToListAsync();

            if (chunks.Any())
            {
                dbContext.QuizChunks.RemoveRange(chunks);
                await dbContext.SaveChangesAsync();
            }
        }

        public async Task<List<QuizChunk>> GetAllAsync(Guid userId)
        {
            return await dbContext.QuizChunks.Where(c => c.UserId == userId).ToListAsync();
        }
        public async Task<QuizChunk?> GetByIdAsync(Guid id)
        {
            return await dbContext.QuizChunks.FirstOrDefaultAsync(c => c.Id == id);
        }

        public async Task<List<QuizChunk>> GetByDocumentAsync(Guid documentId, Guid userId)
        {
            return await dbContext.QuizChunks.Where(c => c.UserId == userId && c.DocumentId == documentId).ToListAsync();
        }

        public async Task<List<QuizChunk>> GetBySubjectAsync(Guid subjectId, Guid userId)
        {
            return await dbContext.QuizChunks.Where(c => c.UserId == userId && c.SubjectId == subjectId).ToListAsync();
        }
    }
}
