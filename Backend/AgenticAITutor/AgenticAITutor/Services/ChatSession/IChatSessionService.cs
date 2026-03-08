using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IChatSessionService
    {
        Task<ServiceResponse<ChatSessionResponse>> CreateSessionAsync(ChatSessionRequest request);
        Task<ServiceResponse<List<ChatSessionResponse>>> GetUserSessionsAsync(Guid userId);
        Task<ServiceResponse<bool>> DeleteSessionAsync (Guid userId, Guid sessioId);
        Task<ServiceResponse<bool>> UpdateSessionAsync(ChatSessionUpdate request);

    }
}
