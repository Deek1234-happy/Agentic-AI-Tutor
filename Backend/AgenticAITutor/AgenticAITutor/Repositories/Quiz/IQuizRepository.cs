using AgenticAITutor.Models;

namespace AgenticAITutor.Repositories
{
    public interface IQuizRepository
    {
        // ── Quiz ────────────────────────────────────────────────────────────
        Task<Quiz?> GetByIdAsync(Guid quizId);
        Task<Quiz?> GetByIdWithQuestionsAsync(Guid quizId);
        Task<Quiz?> GetByIdWithDocumentsAsync(Guid quizId);
        Task<Quiz?> GetByUserAndHashAsync(Guid userId, string hash);
        Task AddAsync(Quiz quiz);
        Task UpdateAsync(Quiz quiz);
        Task DeleteAsync(Quiz quiz);

        // ── Quiz queries ────────────────────────────────────────────────────
        Task<List<Quiz>> GetBySubjectAsync(Guid userId, Guid subjectId);
        Task<(List<Quiz> Items, int TotalCount)> GetUserQuizHistoryAsync(
            Guid userId, Guid? subjectId, string? status, int page, int pageSize);

        // ── Attempt ─────────────────────────────────────────────────────────
        Task<QuizAttempt?> GetAttemptByIdAsync(Guid attemptId);
        Task<QuizAttempt?> GetAttemptWithAnswersAsync(Guid attemptId);
        Task<List<QuizAttempt>> GetAttemptsByQuizAndUserAsync(Guid quizId, Guid userId);
        Task<int> GetAttemptCountAsync(Guid quizId, Guid userId);
        Task AddAttemptAsync(QuizAttempt attempt);
        Task UpdateAttemptAsync(QuizAttempt attempt);

        // ── Answers ─────────────────────────────────────────────────────────
        Task AddAnswersAsync(List<QuizAnswer> answers);

        // ── Questions / Options (used by the Hangfire job) ──────────────────
        Task AddQuestionsWithOptionsAsync(List<QuizQuestion> questions);

        // ── Junction table ───────────────────────────────────────────────────
        Task AddQuizDocumentsAsync(Guid quizId, List<Guid> documentIds);
    }
}
