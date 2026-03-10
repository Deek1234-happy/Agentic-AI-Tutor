using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IChatMessageRepository
    {
        Task<ChatMessage> AddAsync (ChatMessage message);
        Task<List<ChatMessage>> GetBySessionIdAsync(Guid sessionId);
    }
}
