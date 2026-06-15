using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IChatWebSourceRepository
    {
        Task AddAsync (ChatWebSource chatWebSource);
        Task<List<ChatWebSource>> GetByMessageIdAsync (Guid messageId);
        Task AddRangeAsync(IEnumerable<ChatWebSource> chatWebSources);
    }
}
