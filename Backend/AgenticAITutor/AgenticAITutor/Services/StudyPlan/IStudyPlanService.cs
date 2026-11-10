using AgenticAITutor.Models.DTOs.Analytics;
using AgenticAITutor.Models.DTOs.StudyPlan;

namespace AgenticAITutor.Services;

public interface IStudyPlanService
{
    Task<List<ReviewScheduleItemDto>> GetReviewScheduleAsync(Guid userId);
    Task<List<ReviewScheduleItemDto>> GenerateFromWeakTopicsAsync(
        Guid userId,
        List<ConceptMasteryDto> weakTopics);
    Task RecordTopicResultsAsync(
        Guid userId,
        Guid subjectId,
        List<Guid> documentIds,
        Dictionary<string, (int Correct, int Total)> topicResults);
    Task<bool> MarkReviewCompletedAsync(Guid userId, Guid itemId);
}
