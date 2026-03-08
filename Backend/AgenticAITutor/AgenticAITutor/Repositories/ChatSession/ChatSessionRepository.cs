using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class ChatSessionRepository : IChatSessionRepository
    {
        private readonly AppDbContext dbContext;

        public ChatSessionRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task<ChatSession> AddAsync(ChatSession chatSession)
        {
            await dbContext.ChatSessions.AddAsync(chatSession);
            await dbContext.SaveChangesAsync();

            return chatSession;
        }
        public async Task UpdateAsync(ChatSession chatSession)
        {
            dbContext.ChatSessions.Update(chatSession);
            await dbContext.SaveChangesAsync();
        }

        public async Task DeleteAsync(ChatSession chatSession)
        {
            dbContext.ChatSessions.Remove(chatSession);
            await dbContext.SaveChangesAsync();
        }

        public async Task<List<ChatSession>> GetAllAsync(Guid userId)
        {
            return await dbContext.ChatSessions
                .Include(c=>c.Documents)
                .Where(c => c.UserId == userId)
                .OrderByDescending(c=>c.UpdatedAt)
                .ToListAsync();
        }

        public async Task<ChatSession?> GetByIdAsync(Guid id, Guid userId)
        {
            return await dbContext.ChatSessions
                .Include(c=>c.Documents)
                .FirstOrDefaultAsync(c=>c.UserId == userId && c.Id == id);
        }

    }
}
