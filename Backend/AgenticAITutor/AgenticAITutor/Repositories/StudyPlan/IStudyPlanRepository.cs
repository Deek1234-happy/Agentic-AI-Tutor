using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories;

public interface IStudyPlanRepository
{
    Task<List<StudyPlan>> GetUserPlansAsync(Guid userId);
    Task<StudyPlan> GetOrCreatePlanForSubjectAsync(
        Guid userId,
        Guid subjectId,
        List<Guid> documentIds);
    Task<StudyPlanItem?> GetItemByConceptAsync(Guid planId, string conceptName);
    Task<StudyPlanItem?> GetItemForUserAsync(Guid userId, Guid itemId);
    Task<UserTopicProgress?> GetTopicProgressAsync(Guid userId, string conceptRef);
    Task AddItemAsync(StudyPlanItem item);
    Task SaveChangesAsync();
    Task AddTopicProgressAsync(UserTopicProgress progress);
}
