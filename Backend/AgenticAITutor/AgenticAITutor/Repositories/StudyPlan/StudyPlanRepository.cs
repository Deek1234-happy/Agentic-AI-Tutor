using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories;

public class StudyPlanRepository : IStudyPlanRepository
{
    private readonly AppDbContext _db;

    public StudyPlanRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<List<StudyPlan>> GetUserPlansAsync(Guid userId)
        => _db.StudyPlans
            .AsNoTracking()
            .Where(plan => plan.UserId == userId)
            .Include(plan => plan.StudyPlanItems)
            .Include(plan => plan.Documents)
                .ThenInclude(document => document.Subject)
            .ToListAsync();

    public async Task<StudyPlan> GetOrCreatePlanForSubjectAsync(
        Guid userId,
        Guid subjectId,
        List<Guid> documentIds)
    {
        var documentsQuery = _db.Documents
            .Where(document =>
                document.UserId == userId &&
                document.SubjectId == subjectId);

        var documents = documentIds.Count > 0
            ? await documentsQuery.Where(document => documentIds.Contains(document.Id)).ToListAsync()
            : new List<Document>();
        if (documents.Count == 0)
            documents = await documentsQuery.ToListAsync();
        if (documents.Count == 0)
            throw new InvalidOperationException("No documents are available for this subject's revision schedule.");

        var plan = await _db.StudyPlans
            .Include(item => item.StudyPlanItems)
            .Include(item => item.Documents)
            .FirstOrDefaultAsync(item =>
                item.UserId == userId &&
                item.Documents.Any(document => document.SubjectId == subjectId));

        if (plan == null)
        {
            var today = DateOnly.FromDateTime(DateTime.UtcNow);
            plan = new StudyPlan
            {
                UserId = userId,
                StartDate = today,
                EndDate = today.AddYears(10)
            };
            await _db.StudyPlans.AddAsync(plan);
        }

        foreach (var document in documents)
        {
            if (!plan.Documents.Any(existing => existing.Id == document.Id))
                plan.Documents.Add(document);
        }

        await _db.SaveChangesAsync();
        return plan;
    }

    public Task<StudyPlanItem?> GetItemByConceptAsync(Guid planId, string conceptName)
        => _db.StudyPlanItems.FirstOrDefaultAsync(item =>
            item.PlanId == planId &&
            item.ConceptRef.ToLower() == conceptName.ToLower());

    public Task<StudyPlanItem?> GetItemForUserAsync(Guid userId, Guid itemId)
        => _db.StudyPlanItems
            .Include(item => item.Plan)
            .FirstOrDefaultAsync(item =>
                item.Id == itemId &&
                item.Plan != null &&
                item.Plan.UserId == userId);

    public Task<UserTopicProgress?> GetTopicProgressAsync(Guid userId, string conceptRef)
        => _db.UserTopicProgresses.FirstOrDefaultAsync(progress =>
            progress.UserId == userId &&
            progress.ConceptRef == conceptRef);

    public async Task AddItemAsync(StudyPlanItem item)
        => await _db.StudyPlanItems.AddAsync(item);

    public Task SaveChangesAsync()
        => _db.SaveChangesAsync();

    public async Task AddTopicProgressAsync(UserTopicProgress progress)
        => await _db.UserTopicProgresses.AddAsync(progress);
}
