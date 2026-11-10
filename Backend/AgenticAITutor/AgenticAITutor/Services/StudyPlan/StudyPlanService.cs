using System.Security.Cryptography;
using System.Text;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs.Analytics;
using AgenticAITutor.Models.DTOs.StudyPlan;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services;

public class StudyPlanService : IStudyPlanService
{
    private readonly IStudyPlanRepository _repository;

    public StudyPlanService(IStudyPlanRepository repository)
    {
        _repository = repository;
    }

    public async Task<List<ReviewScheduleItemDto>> GetReviewScheduleAsync(Guid userId)
    {
        var plans = await _repository.GetUserPlansAsync(userId);
        var topicProgress = new Dictionary<string, UserTopicProgress>(StringComparer.Ordinal);

        var result = new List<ReviewScheduleItemDto>();
        foreach (var plan in plans)
        {
            var subject = plan.Documents
                .Select(document => document.Subject)
                .FirstOrDefault(item => item != null);
            if (subject == null)
                continue;

            foreach (var item in plan.StudyPlanItems)
            {
                var progressRef = BuildProgressReference(subject.Id, item.ConceptRef);
                if (!topicProgress.TryGetValue(progressRef, out var progress))
                {
                    progress = await _repository.GetTopicProgressAsync(userId, progressRef);
                    if (progress != null)
                        topicProgress[progressRef] = progress;
                }

                int? accuracy = progress?.MasteryScore is double score
                    ? (int)Math.Round(score)
                    : null;

                result.Add(new ReviewScheduleItemDto
                {
                    Id = item.Id,
                    SubjectId = subject.Id,
                    SubjectName = subject.Name,
                    ConceptName = item.ConceptRef,
                    ScheduledDate = item.ScheduledDate,
                    EstimatedMinutes = item.EstimatedTime ?? 15,
                    Accuracy = accuracy,
                    Completed = item.Completed ?? false,
                    Status = GetStatus(item.Completed ?? false, accuracy)
                });
            }
        }

        return result
            .OrderBy(item => item.Completed)
            .ThenBy(item => item.ScheduledDate)
            .ThenBy(item => item.SubjectName)
            .ToList();
    }

    public async Task<List<ReviewScheduleItemDto>> GenerateFromWeakTopicsAsync(
        Guid userId,
        List<ConceptMasteryDto> weakTopics)
    {
        foreach (var topic in weakTopics)
        {
            if (topic.SubjectId == Guid.Empty || string.IsNullOrWhiteSpace(topic.ConceptName))
                continue;

            var plan = await _repository.GetOrCreatePlanForSubjectAsync(
                userId,
                topic.SubjectId,
                topic.SourceDocumentIds ?? new List<Guid>());
            var item = await _repository.GetItemByConceptAsync(plan.Id, topic.ConceptName);
            if (item != null)
                continue;

            await _repository.AddItemAsync(new StudyPlanItem
            {
                PlanId = plan.Id,
                ConceptRef = topic.ConceptName.Trim(),
                EstimatedTime = 15,
                ScheduledDate = DateOnly.FromDateTime(DateTime.UtcNow),
                Completed = false
            });

            await SaveTopicProgressAsync(
                userId,
                topic.SubjectId,
                topic.ConceptName,
                topic.Accuracy);
        }

        return await GetReviewScheduleAsync(userId);
    }

    public async Task RecordTopicResultsAsync(
        Guid userId,
        Guid subjectId,
        List<Guid> documentIds,
        Dictionary<string, (int Correct, int Total)> topicResults)
    {
        foreach (var (conceptName, result) in topicResults)
        {
            if (string.IsNullOrWhiteSpace(conceptName) || result.Total <= 0)
                continue;

            var accuracy = (int)Math.Round((double)result.Correct / result.Total * 100);
            var intervalDays = accuracy switch
            {
                < 70 => 1,
                < 90 => 3,
                _ => 14
            };
            var plan = await _repository.GetOrCreatePlanForSubjectAsync(
                userId,
                subjectId,
                documentIds);
            var item = await _repository.GetItemByConceptAsync(plan.Id, conceptName.Trim());
            var scheduledDate = DateOnly.FromDateTime(DateTime.UtcNow).AddDays(intervalDays);

            if (item == null)
            {
                await _repository.AddItemAsync(new StudyPlanItem
                {
                    PlanId = plan.Id,
                    ConceptRef = conceptName.Trim(),
                    EstimatedTime = 15,
                    ScheduledDate = scheduledDate,
                    Completed = false
                });
            }
            else
            {
                item.ScheduledDate = scheduledDate;
                item.EstimatedTime = 15;
                item.Completed = false;
            }

            await SaveTopicProgressAsync(userId, subjectId, conceptName, accuracy);
        }
    }

    public async Task<bool> MarkReviewCompletedAsync(Guid userId, Guid itemId)
    {
        var item = await _repository.GetItemForUserAsync(userId, itemId);
        if (item == null)
            return false;

        item.Completed = true;
        await _repository.SaveChangesAsync();
        return true;
    }

    private async Task SaveTopicProgressAsync(
        Guid userId,
        Guid subjectId,
        string conceptName,
        int accuracy)
    {
        var progressRef = BuildProgressReference(subjectId, conceptName);
        var updatedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Unspecified);
        var progress = await _repository.GetTopicProgressAsync(userId, progressRef);
        if (progress == null)
        {
            await _repository.AddTopicProgressAsync(new UserTopicProgress
            {
                UserId = userId,
                ConceptRef = progressRef,
                MasteryScore = accuracy,
                LastUpdated = updatedAt
            });
        }
        else
        {
            progress.MasteryScore = accuracy;
            progress.LastUpdated = updatedAt;
        }

        await _repository.SaveChangesAsync();
    }

    private static string BuildProgressReference(Guid subjectId, string conceptName)
    {
        var normalizedConcept = conceptName.Trim().ToUpperInvariant();
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(normalizedConcept)));
        return $"{subjectId:N}:{hash}";
    }

    private static string GetStatus(bool completed, int? accuracy)
    {
        if (completed)
            return "Reviewed";
        if (accuracy >= 90)
            return "Mastered";
        if (accuracy >= 70)
            return "Improving";
        return "Needs review";
    }
}
