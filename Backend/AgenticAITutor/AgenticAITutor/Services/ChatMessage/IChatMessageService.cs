using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.DTOs.ChatMessage;

namespace AgenticAITutor.Services
{
    public interface IChatMessageService
    {
        Task<ServiceResponse<AIMessageResponse>> SendAIMessageAsync(UserMessageRequest request);
        Task<ServiceResponse<WebSearchResponse>> SendWebMessageAsync(UserMessageRequest request);
        Task<ServiceResponse<List<ChatMessageResponse>>> GetSessionMessagesAsync(Guid userId, Guid sessionId);
        Task<ServiceResponse<string>> SpeechToTextAsync(IFormFile audioFile);
        Task<ServiceResponse<string>> TextToSpeechAsync(Guid messageId, Guid userId);
    }
}
