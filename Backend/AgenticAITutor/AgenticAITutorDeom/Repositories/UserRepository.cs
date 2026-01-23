using AgenticAITutorDeom.Data;
using AgenticAITutorDeom.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Repositories
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
