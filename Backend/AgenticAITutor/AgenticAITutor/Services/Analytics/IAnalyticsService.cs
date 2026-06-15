using System;
using System.Threading.Tasks;
using AgenticAITutor.Models.DTOs.Analytics;

namespace AgenticAITutor.Services.Analytics;

public interface IAnalyticsService
{
    Task<ProgressDashboardResponseDto> GetProgressDashboardAsync(Guid userId);
}
