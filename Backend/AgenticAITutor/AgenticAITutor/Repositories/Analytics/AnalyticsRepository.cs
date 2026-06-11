using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories.Analytics;

public class AnalyticsRepository : IAnalyticsRepository
{
    private readonly AppDbContext _context;

    public AnalyticsRepository(AppDbContext context)
    {
        _context = context;
    }

    public async Task<List<QuizAttempt>> GetUserAttemptsWithDetailsAsync(Guid userId)
    {
        return await _context.QuizAttempts
            .AsNoTracking()
            .Include(a => a.Quiz)
                .ThenInclude(q => q.Subject)
            .Include(a => a.QuizAnswers)
                .ThenInclude(qa => qa.Question)
            .Where(a => a.UserId == userId && a.FinishedAt != null)
            .ToListAsync();
    }
}
