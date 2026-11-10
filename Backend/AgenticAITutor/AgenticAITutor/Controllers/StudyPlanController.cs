using AgenticAITutor.Extensions;
using AgenticAITutor.Models.DTOs.StudyPlan;
using AgenticAITutor.Services;
using AgenticAITutor.Services.Analytics;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers;

[Route("api/[controller]")]
[ApiController]
[Authorize]
public class StudyPlanController : ControllerBase
{
    private readonly IAnalyticsService _analyticsService;
    private readonly IStudyPlanService _studyPlanService;

    public StudyPlanController(
        IAnalyticsService analyticsService,
        IStudyPlanService studyPlanService)
    {
        _analyticsService = analyticsService;
        _studyPlanService = studyPlanService;
    }

    [HttpGet("reviews")]
    [ProducesResponseType(typeof(List<ReviewScheduleItemDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetReviewSchedule()
    {
        var userId = User.GetUserId();
        if (userId == Guid.Empty)
            return Unauthorized("Invalid Token.");

        return Ok(await _studyPlanService.GetReviewScheduleAsync(userId));
    }

    [HttpPost("generate")]
    [ProducesResponseType(typeof(List<ReviewScheduleItemDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GenerateFromWeakTopics()
    {
        var userId = User.GetUserId();
        if (userId == Guid.Empty)
            return Unauthorized("Invalid Token.");

        var progress = await _analyticsService.GetProgressDashboardAsync(userId);
        var schedule = await _studyPlanService.GenerateFromWeakTopicsAsync(
            userId,
            progress.WeakConcepts);

        return Ok(schedule);
    }

    [HttpPost("reviews/{itemId:guid}/complete")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> MarkReviewCompleted(Guid itemId)
    {
        var userId = User.GetUserId();
        if (userId == Guid.Empty)
            return Unauthorized("Invalid Token.");

        var updated = await _studyPlanService.MarkReviewCompletedAsync(userId, itemId);
        return updated ? NoContent() : NotFound("Review item not found.");
    }
}
