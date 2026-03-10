using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class ChatMessageRepository : IChatMessageRepository
    {
        private readonly AppDbContext dbContext;

        public ChatMessageRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task<ChatMessage> AddAsync(ChatMessage message)
        {
            await dbContext.ChatMessages.AddAsync(message);
            await dbContext.SaveChangesAsync();

            return message;
        }

        public async Task<List<ChatMessage>> GetBySessionIdAsync(Guid sessionId)
        {
            return await dbContext.ChatMessages
                .Include(c => c.Chunks)
                .Where(c => c.SessionId == sessionId)
                .OrderBy(c => c.CreatedAt)
                .ToListAsync();
        }
    }
}
