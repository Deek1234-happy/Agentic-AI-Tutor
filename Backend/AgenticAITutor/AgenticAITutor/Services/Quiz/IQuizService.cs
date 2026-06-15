using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IQuizService
    {
        Task<ServiceResponse<QuizInitiateResponse>> InitiateAsync(Guid userId, QuizInitiateRequest request);
        Task<ServiceResponse<QuizStatusResponse>> GetStatusAsync(Guid userId, Guid quizId);
        Task<ServiceResponse<QuizStartResponse>> StartAsync(Guid userId, Guid quizId);
        Task<ServiceResponse<QuizSubmitResponse>> SubmitAsync(Guid userId, Guid quizId, QuizSubmitRequest request);
        Task<ServiceResponse<List<QuizAttemptSummary>>> GetAttemptsAsync(Guid userId, Guid quizId);
        Task<ServiceResponse<QuizReviewResponse>> GetReviewAsync(Guid userId, Guid attemptId);
        Task<ServiceResponse<List<QuizHistoryItem>>> GetHistoryAsync(Guid userId, QuizHistoryFilter filter);
        Task<ServiceResponse<List<QuizHistoryItem>>> GetBySubjectAsync(Guid userId, Guid subjectId);
    }
}
