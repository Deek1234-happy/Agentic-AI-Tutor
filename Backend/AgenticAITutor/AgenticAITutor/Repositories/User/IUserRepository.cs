using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IUserRepository
    {
        Task AddAsync (User user);
        Task UpdateAsync(User user);
        Task DeleteAsync(User user);
        Task<User?> GetByEmailAsync (string email);
        Task<User?> GetByIdAsync(Guid id);
        Task<(int DocumentCount, int QuizCount, int SubjectCount)> GetStatsAsync(Guid userId);
    }
}
