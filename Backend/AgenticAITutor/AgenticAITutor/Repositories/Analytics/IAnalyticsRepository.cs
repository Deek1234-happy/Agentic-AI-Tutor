using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories.Analytics;

public interface IAnalyticsRepository
{
    Task<List<QuizAttempt>> GetUserAttemptsWithDetailsAsync(Guid userId);
}
