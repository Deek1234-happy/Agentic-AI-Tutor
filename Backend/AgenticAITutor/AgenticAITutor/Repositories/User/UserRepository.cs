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

        public async Task AddAsync(User user)
        {
            await dbContext.Users.AddAsync(user);
            await dbContext.SaveChangesAsync();
        }

        public async Task UpdateAsync(User user)
        {
            dbContext.Users.Update(user);
            await dbContext.SaveChangesAsync();
        }

        public async Task DeleteAsync(User user)
        {
            dbContext.Users.Remove(user);
            await dbContext.SaveChangesAsync();
        }

        public async Task<User?> GetByEmailAsync(string email)
        {
            return await dbContext.Users.FirstOrDefaultAsync(u => u.Email == email);
        }

        public async Task<User?> GetByIdAsync(Guid id)
        {
            return await dbContext.Users.FirstOrDefaultAsync(u => u.Id == id);
        }

        public async Task<(int DocumentCount, int QuizCount, int SubjectCount)> GetStatsAsync(Guid userId)
        {
            var docCount = await dbContext.Documents.CountAsync(u => u.UserId == userId);
            var quizCount = await dbContext.Quizzes.CountAsync(u => u.UserId == userId);
            var subCount = await dbContext.Subjects.CountAsync(u => u.UserId == userId);

            return (docCount, quizCount, subCount);
        }

    }
}
