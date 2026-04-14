using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IDocumentChunkRepository
    {
        Task AddAsync(DocumentChunk chunk);
        Task AddRangeAsync(List<DocumentChunk> chunks);
        Task UpdateAsync(DocumentChunk chunk);
        Task DeleteAsync(DocumentChunk chunk);
        Task DeleteByDocumentAsync(Guid documentId);
        Task<DocumentChunk?> GetByIdAsync(Guid id);
        Task<List<DocumentChunk>> GetAllAsync(Guid userId);
        Task<List<DocumentChunk>> GetByDocumentAsync(Guid documentId, Guid userId);
        Task<List<DocumentChunk>> GetBySubjectAsync(Guid subjectId, Guid userId);

    }
}
