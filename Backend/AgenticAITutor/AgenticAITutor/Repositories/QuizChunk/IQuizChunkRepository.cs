using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IQuizChunkRepository
    {
        Task AddAsync(QuizChunk chunk);
        Task AddRangeAsync(List<QuizChunk> chunks);
        Task UpdateAsync(QuizChunk chunk);
        Task DeleteAsync(QuizChunk chunk);
        Task DeleteByDocumentAsync(Guid documentId);
        Task<QuizChunk?> GetByIdAsync(Guid id);
        Task<List<QuizChunk>> GetAllAsync(Guid userId);
        Task<List<QuizChunk>> GetByDocumentAsync(Guid documentId, Guid userId);
        Task<List<QuizChunk>> GetBySubjectAsync(Guid subjectId, Guid userId);
    }
}
