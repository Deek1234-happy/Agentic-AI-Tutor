using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services
{
    public class ChatMessageService : IChatMessageService
    {
        private readonly IChatMessageRepository messageRepository;
        private readonly IChatSessionRepository sessionRepository;
        private readonly IDocumentChunkRepository chunkRepository;
        private readonly HttpClient httpClient;
        private readonly IConfiguration configuration;
        private readonly IChatWebSourceRepository webSourceRepository;

        public ChatMessageService(
            IChatMessageRepository messageRepository, 
            IChatSessionRepository sessionRepository, 
            IDocumentChunkRepository chunkRepository, 
            HttpClient httpClient,
            IConfiguration configuration,
            IChatWebSourceRepository webSourceRepository)
        {
            this.messageRepository = messageRepository;
            this.sessionRepository = sessionRepository;
            this.chunkRepository = chunkRepository;
            this.httpClient = httpClient;
            this.configuration = configuration;
            this.webSourceRepository = webSourceRepository;
        }

        public async Task<ServiceResponse<AIMessageResponse>> SendAIMessageAsync(UserMessageRequest request)
        {
            var response = new ServiceResponse<AIMessageResponse>();

            // Validate That The Session Is Exist and Belongs to The User
            var session = await sessionRepository.GetByIdAsync(request.SessionId, request.UserId);
            if (session == null)
            {
                response.Success = false;
                response.Message = "Session not Found or Unauthorized.";

                return response;
            }

            foreach(var doc in session.Documents)
            {
                request?.AllowedDocumentIds?.Add(doc.Id);
            }

            // Save The User Message to The Database 
            var userMessage = new ChatMessage
            {
                SessionId = request.SessionId,
                Role = "user",
                Content = request.UserMessage ?? string.Empty,
                CreatedAt = DateTime.Now
            };
            await messageRepository.AddAsync(userMessage);

            // Update The Session Updated Time
            session.UpdatedAt = DateTime.Now;
            await sessionRepository.UpdateAsync(session);

            // Call The AI Endpoint 
            string? aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
            string? chatPath = configuration["AIService:ChatPath"] ?? "chat/";

            string? aiURL = $"{aiBaseURL.TrimEnd('/')}/{chatPath.TrimStart('/')}";


            AIMessageResponse? aiResponse = null;
            try
            {
                httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
                var httpResponse = await httpClient.PostAsJsonAsync(aiURL, request);
                if (!httpResponse.IsSuccessStatusCode)
                {
                    string errorBody = await httpResponse.Content.ReadAsStringAsync();
                    response.Success = false;
                    response.Message = $"AI API Failed! Status: {httpResponse.StatusCode}. Error Details: {errorBody}";
                    return response;
                }

                aiResponse = await httpResponse.Content.ReadFromJsonAsync<AIMessageResponse>();
            }
            catch (Exception ex)
            {
                response.Success = false;
                response.Message = $"Failed to communicate with the AI service: {ex.Message}";

                return response;
            }

            // Save The AI's Answer to The Database 
            if (aiResponse != null)
            {
                var aiMessage = new ChatMessage
                {
                    SessionId = request.SessionId,
                    Role = "assistant",
                    Content = aiResponse.AIMessage ?? "No Response Generated.",
                    CreatedAt = DateTime.Now,
                    ConfidenceScore = aiResponse.ConfidenceScore
                };
                // Add The Message Citation in The Database 
                foreach (var citation in aiResponse.UsedChunks)
                {
                    DocumentChunk chunk = await chunkRepository.GetByIdAsync(citation.ChunkId);
                    if (chunk != null)
                        aiMessage.Chunks.Add(chunk);
                }

                await messageRepository.AddAsync(aiMessage);

            }
            response.Data = aiResponse;
            response.Success = true;
            return response;

        }
        //public async Task<ServiceResponse<AIMessageResponse>> SendMessageAsync(UserMessageRequest request)
        //{
        //    var response = new ServiceResponse<AIMessageResponse>();

        //    // Validate That The Session Is Exist and Belongs to The User
        //    var session = await sessionRepository.GetByIdAsync(request.SessionId, request.UserId);
        //    if (session == null)
        //    {
        //        response.Success = false;
        //        response.Message = "Session not Found or Unauthorized.";

        //        return response;
        //    }

        //    // Save The User Message to The Database 
        //    var userMessage = new ChatMessage
        //    {
        //        SessionId = request.SessionId,
        //        Role = "user",
        //        Content = request.UserMessage ?? string.Empty,
        //        CreatedAt = DateTime.Now
        //    };
        //    await messageRepository.AddAsync(userMessage);

        //    // Update The Session Updated Time
        //    session.UpdatedAt = DateTime.Now;
        //    await sessionRepository.UpdateAsync(session);

        //    // Call The AI Endpoint 
        //    string aiURL = "https://localhost:7257/api/AIRetrieval/retrieve";

        //    AIMessageResponse? aiResponse = null;
        //    try
        //    {
        //        var httpResponse = await httpClient.PostAsJsonAsync(aiURL, request);
        //        httpResponse.EnsureSuccessStatusCode();

        //        aiResponse = await httpResponse.Content.ReadFromJsonAsync<AIMessageResponse>();
        //    }
        //    catch (Exception ex)
        //    {
        //        response.Success = false;
        //        response.Message = $"Failed to communicate with the AI service: {ex.Message}";

        //        return response;
        //    }

        //    // Save The AI's Answer to The Database 
        //    if(aiResponse != null)
        //    {
        //        var aiMessage = new ChatMessage
        //        {
        //            SessionId= request.SessionId,
        //            Role = "AI",
        //            Content = aiResponse.AIMessage ?? "No Response Generated.",
        //            CreatedAt = DateTime.Now,
        //            ConfidenceScore = aiResponse.UsedChunks.FirstOrDefault()?.RelevanceScore
        //        };
        //        // Add The Message Citation in The Database 
        //        foreach (var citation in aiResponse.UsedChunks)
        //        {
        //            DocumentChunk chunk = await chunkRepository.GetByIdAsync(citation.ChunkId);
        //            if(chunk != null)
        //                aiMessage.Chunks.Add(chunk);
        //        }

        //        await messageRepository.AddAsync(aiMessage);

        //    }
        //    response.Data = aiResponse;
        //    response.Success = true;
        //    return response;

        //}

        public async Task<ServiceResponse<WebSearchResponse>> SendWebMessageAsync(UserMessageRequest request)
        {

            WebSearchRequest webSearchRequest = new WebSearchRequest
            {
                Question = request.UserMessage,
                SessionId = request.SessionId
            };

            var response = new ServiceResponse<WebSearchResponse>();

            // Validate That The Session Is Exist and Belongs to The User
            var session = await sessionRepository.GetByIdAsync(request.SessionId, request.UserId);
            if (session == null)
            {
                response.Success = false;
                response.Message = "Session not Found or Unauthorized.";

                return response;
            }

            //foreach (var doc in session.Documents)
            //{
            //    request?.AllowedDocumentIds?.Add(doc.Id);
            //}

            // Save The User Message to The Database 
            var userMessage = new ChatMessage
            {
                SessionId = request.SessionId,
                Role = "user",
                Content = request.UserMessage ?? string.Empty,
                CreatedAt = DateTime.Now
            };
            await messageRepository.AddAsync(userMessage);

            // Update The Session Updated Time
            session.UpdatedAt = DateTime.Now;
            await sessionRepository.UpdateAsync(session);

            // Call The AI Endpoint 
            string? aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
            string? webSearchPath = configuration["AIService:WebSearchPath"] ?? "searchweb";

            string? webSearchURL = $"{aiBaseURL.TrimEnd('/')}/{webSearchPath.TrimStart('/')}";


            WebSearchResponse? webSearchResponse = null;
            try
            {
                httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
                var httpResponse = await httpClient.PostAsJsonAsync(webSearchURL, webSearchRequest);
                if (!httpResponse.IsSuccessStatusCode)
                {
                    string errorBody = await httpResponse.Content.ReadAsStringAsync();
                    response.Success = false;
                    response.Message = $"AI API Failed! Status: {httpResponse.StatusCode}. Error Details: {errorBody}";
                    return response;
                }

                webSearchResponse = await httpResponse.Content.ReadFromJsonAsync<WebSearchResponse>();
            }
            catch (Exception ex)
            {
                response.Success = false;
                response.Message = $"Failed to communicate with the AI service: {ex.Message}";

                return response;
            }

            // Save The AI's Answer to The Database 
            if (webSearchResponse != null)
            {
                var webSearchMessage = new ChatMessage
                {
                    SessionId = request.SessionId,
                    Role = "web",
                    Content = webSearchResponse.Answer ?? "No Response Generated.",
                    CreatedAt = DateTime.Now,
                    ConfidenceScore = 0
                };

                await messageRepository.AddAsync(webSearchMessage);

                // Add The Message Web Sources in The Database 
                foreach (var source in webSearchResponse.Sources)
                {
                    ChatWebSource webSource = new ChatWebSource
                    {
                        Domain = source.Domain,
                        Title = source.Title,
                        Url = source.URL,
                        MessageId = webSearchMessage.Id
                    };

                    await webSourceRepository.AddAsync(webSource);
                }


            }
            response.Data = webSearchResponse;
            response.Success = true;
            return response;

        }


        public async Task<ServiceResponse<List<ChatMessage>>> GetSessionMessagesAsync(Guid userId, Guid sessionId)
        {
            var response = new ServiceResponse<List<ChatMessage>>();

            // 1. Security Check: Ensure the user actually owns this session
            var session = await sessionRepository.GetByIdAsync(userId, sessionId);
            if (session == null)
            {
                response.Success = false;
                response.Message = "Session not found or unauthorized.";
                return response;
            }

            // 2. Fetch the messages using the repository we built earlier
            var messages = await messageRepository.GetBySessionIdAsync(sessionId);

            response.Data = messages;
            response.Success = true;
            return response;
        }

    }
}
