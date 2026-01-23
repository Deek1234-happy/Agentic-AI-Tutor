using AgenticAITutorDeom.Models;

namespace AgenticAITutorDeom.Repositories
{
    public interface IUserRepository
    {
        Task<user?> GetByEmailAsync (string email);
        Task AddAsync (user user);
    }
}
