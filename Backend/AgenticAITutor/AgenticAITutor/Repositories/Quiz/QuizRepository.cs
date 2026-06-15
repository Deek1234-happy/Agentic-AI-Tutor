using AgenticAITutor.Data;
using AgenticAITutor.Models;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Repositories
{
    public class QuizRepository : IQuizRepository
    {
        private readonly AppDbContext _db;

        public QuizRepository(AppDbContext db)
        {
            _db = db;
        }

        // ── Quiz ─────────────────────────────────────────────────────────────

        public async Task<Quiz?> GetByIdAsync(Guid quizId)
            => await _db.Quizzes.FirstOrDefaultAsync(q => q.Id == quizId);

        public async Task<Quiz?> GetByIdWithQuestionsAsync(Guid quizId)
            => await _db.Quizzes
                .Include(q => q.QuizQuestions.OrderBy(qq => qq.SlotIndex))
                    .ThenInclude(qq => qq.QuizOptions)
                .Include(q => q.QuizQuestions)
                    .ThenInclude(qq => qq.Chunk) // citation chunks
                .FirstOrDefaultAsync(q => q.Id == quizId);

        public async Task<Quiz?> GetByIdWithDocumentsAsync(Guid quizId)
            => await _db.Quizzes
                .Include(q => q.Documents)
                .FirstOrDefaultAsync(q => q.Id == quizId);

        public async Task<Quiz?> GetByUserAndHashAsync(Guid userId, string hash)
            => await _db.Quizzes
                .FirstOrDefaultAsync(q => q.UserId == userId && q.GenerationHash == hash);

        public async Task AddAsync(Quiz quiz)
        {
            await _db.Quizzes.AddAsync(quiz);
            await _db.SaveChangesAsync();
        }

        public async Task UpdateAsync(Quiz quiz)
        {
            _db.Quizzes.Update(quiz);
            await _db.SaveChangesAsync();
        }

        public async Task DeleteAsync(Quiz quiz)
        {
            _db.Quizzes.Remove(quiz);
            await _db.SaveChangesAsync();
        }

        // ── Quiz queries ──────────────────────────────────────────────────────

        public async Task<List<Quiz>> GetBySubjectAsync(Guid userId, Guid subjectId)
            => await _db.Quizzes
                .Where(q => q.UserId == userId && q.SubjectId == subjectId)
                .Include(q => q.Subject)
                .Include(q=>q.QuizAttempts)
                .OrderByDescending(q => q.CreatedAt)
                .ToListAsync();

        public async Task<(List<Quiz> Items, int TotalCount)> GetUserQuizHistoryAsync(
            Guid userId, Guid? subjectId, string? status, int page, int pageSize)
        {
            var query = _db.Quizzes
                .Where(q => q.UserId == userId);

            if (subjectId.HasValue)
                query = query.Where(q => q.SubjectId == subjectId.Value);

            if (!string.IsNullOrWhiteSpace(status))
                query = query.Where(q => q.Status == status);

            var total = await query.CountAsync();
            var items = await query
                .OrderByDescending(q => q.CreatedAt)
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .Include(q => q.Subject)
                .Include(q => q.QuizAttempts)
                .ToListAsync();

            return (items, total);
        }

        // ── Attempt ───────────────────────────────────────────────────────────

        public async Task<QuizAttempt?> GetAttemptByIdAsync(Guid attemptId)
            => await _db.QuizAttempts.FirstOrDefaultAsync(a => a.Id == attemptId);

        public async Task<QuizAttempt?> GetAttemptWithAnswersAsync(Guid attemptId)
            => await _db.QuizAttempts
                .Include(a => a.QuizAnswers)
                    .ThenInclude(ans => ans.Question)
                        .ThenInclude(q => q.QuizOptions)
                .Include(a => a.QuizAnswers)
                    .ThenInclude(ans => ans.Question)
                        .ThenInclude(q => q.Chunk)
                .FirstOrDefaultAsync(a => a.Id == attemptId);

        public async Task<List<QuizAttempt>> GetAttemptsByQuizAndUserAsync(Guid quizId, Guid userId)
            => await _db.QuizAttempts
                .Where(a => a.QuizId == quizId && a.UserId == userId)
                .OrderBy(a => a.AttemptNumber)
                .ToListAsync();

        public async Task<int> GetAttemptCountAsync(Guid quizId, Guid userId)
            => await _db.QuizAttempts
                .CountAsync(a => a.QuizId == quizId && a.UserId == userId);

        public async Task AddAttemptAsync(QuizAttempt attempt)
        {
            await _db.QuizAttempts.AddAsync(attempt);
            await _db.SaveChangesAsync();
        }

        public async Task UpdateAttemptAsync(QuizAttempt attempt)
        {
            _db.QuizAttempts.Update(attempt);
            await _db.SaveChangesAsync();
        }

        // ── Answers ────────────────────────────────────────────────────────────

        public async Task AddAnswersAsync(List<QuizAnswer> answers)
        {
            await _db.QuizAnswers.AddRangeAsync(answers);
            await _db.SaveChangesAsync();
        }

        // ── Questions / Options ────────────────────────────────────────────────

        public async Task AddQuestionsWithOptionsAsync(List<QuizQuestion> questions)
        {
            await _db.QuizQuestions.AddRangeAsync(questions);
            await _db.SaveChangesAsync();
        }

        // ── Junction table ─────────────────────────────────────────────────────

        public async Task AddQuizDocumentsAsync(Guid quizId, List<Guid> documentIds)
        {
            // Load the quiz with its Documents collection so EF can manage the junction rows
            var quiz = await _db.Quizzes
                .Include(q => q.Documents)
                .FirstOrDefaultAsync(q => q.Id == quizId);

            if (quiz == null) return;

            var docs = await _db.Documents
                .Where(d => documentIds.Contains(d.Id))
                .ToListAsync();

            foreach (var doc in docs)
                quiz.Documents.Add(doc);

            await _db.SaveChangesAsync();
        }
    }
}
