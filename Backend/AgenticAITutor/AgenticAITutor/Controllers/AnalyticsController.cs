using System;
using System.Threading.Tasks;
using AgenticAITutor.Extensions;
using AgenticAITutor.Models.DTOs.Analytics;
using AgenticAITutor.Services.Analytics;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers;

[Route("api/[controller]")]
[ApiController]
[Authorize]
public class AnalyticsController : ControllerBase
{
    private readonly IAnalyticsService _analyticsService;

    public AnalyticsController(IAnalyticsService analyticsService)
    {
        _analyticsService = analyticsService;
    }

    /// <summary>
    /// Gets the progress and analytics dashboard for the current user.
    /// </summary>
    /// <returns>A ProgressDashboardResponseDto with key KPIs, monthly performance, subject progress, and weak concepts.</returns>
    [HttpGet("progress")]
    [ProducesResponseType(typeof(ProgressDashboardResponseDto), 200)]
    [ProducesResponseType(typeof(string), 401)]
    public async Task<IActionResult> GetProgressDashboard()
    {
        var userId = User.GetUserId();
        if (userId == Guid.Empty)
            return Unauthorized("Invalid Token.");

        var dashboardData = await _analyticsService.GetProgressDashboardAsync(userId);
        
        return Ok(dashboardData);
    }
}
