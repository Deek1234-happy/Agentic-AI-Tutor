using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class ChatWebSourceRepository : IChatWebSourceRepository
    {
        private readonly AppDbContext dbContext;

        public ChatWebSourceRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task AddAsync(ChatWebSource chatWebSource)
        {
            await dbContext.ChatWebSources.AddAsync(chatWebSource);
            await dbContext.SaveChangesAsync();
        }

        public async Task<List<ChatWebSource>> GetByMessageIdAsync(Guid messageId)
        {
            return await dbContext.ChatWebSources.Where(c => c.MessageId == messageId).ToListAsync();
        }

        public async Task AddRangeAsync (IEnumerable<ChatWebSource> chatWebSources)
        {
            await dbContext.ChatWebSources.AddRangeAsync(chatWebSources);
            await dbContext.SaveChangesAsync();
        }
    }
}
