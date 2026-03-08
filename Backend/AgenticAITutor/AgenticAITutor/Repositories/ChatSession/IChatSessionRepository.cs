using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IChatSessionRepository
    {
        Task<ChatSession> AddAsync(ChatSession chatSession);
        Task<List<ChatSession>> GetAllAsync(Guid userId);
        Task<ChatSession?> GetByIdAsync (Guid id, Guid userId);
        Task UpdateAsync (ChatSession chatSession);
        Task DeleteAsync (ChatSession chatSession);
    }
}
