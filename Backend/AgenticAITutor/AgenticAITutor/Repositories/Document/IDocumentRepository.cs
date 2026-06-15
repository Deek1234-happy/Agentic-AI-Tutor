using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Repositories
{
    public interface IDocumentRepository
    {
        Task AddAsync(Document document);
        Task UpdateAsync(Document document);
        Task DeleteAsync(Document document);
        Task<Document?> GetByIdAsync(Guid id);
        Task<Document?> GetByHashAsync(string contentHash, Guid userId);
        Task<List<Document>> GetAllAsync(Guid userId);
        Task<List<Document>> GetBySubjectAsync (Guid userId, Guid subjectId);
        Task<List<Document>> GetDocumentsByIdsAsync(List<Guid> documentIds, Guid userId);

    }
}
