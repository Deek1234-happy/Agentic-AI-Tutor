using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IChatMessageService
    {
        Task<ServiceResponse<AIMessageResponse>> SendAIMessageAsync(UserMessageRequest request);
        Task<ServiceResponse<WebSearchResponse>> SendWebMessageAsync(UserMessageRequest request);
        Task<ServiceResponse<List<ChatMessage>>> GetSessionMessagesAsync(Guid userId, Guid sessionId);
    }
}
