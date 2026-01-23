using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IUserRepository
    {
        Task<user?> GetByEmailAsync (string email);
        Task AddAsync (user user);
    }
}
