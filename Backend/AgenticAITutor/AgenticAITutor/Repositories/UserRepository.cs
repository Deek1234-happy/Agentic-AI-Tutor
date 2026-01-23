using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class UserRepository : IUserRepository
    {
        private readonly AppDbContext dbContext;

        public UserRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task<user?> GetByEmailAsync(string email)
        {
            return await dbContext.users.FirstOrDefaultAsync(u => u.email == email);
        }
        public async Task AddAsync(user user)
        {
            dbContext.users.Add(user);
            await dbContext.SaveChangesAsync();
        }

    }
}
