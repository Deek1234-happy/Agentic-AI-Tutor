using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.DTOs.ChatMessage;
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
        private readonly IFileStorageService fileStorageService;

        public ChatMessageService(
            IChatMessageRepository messageRepository, 
            IChatSessionRepository sessionRepository, 
            IDocumentChunkRepository chunkRepository, 
            HttpClient httpClient,
            IConfiguration configuration,
            IChatWebSourceRepository webSourceRepository,
            IFileStorageService fileStorageService)
        {
            this.messageRepository = messageRepository;
            this.sessionRepository = sessionRepository;
            this.chunkRepository = chunkRepository;
            this.httpClient = httpClient;
            this.configuration = configuration;
            this.webSourceRepository = webSourceRepository;
            this.fileStorageService = fileStorageService;
            this.httpClient.Timeout = TimeSpan.FromMinutes(10);
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

        public async Task<ServiceResponse<AIAudioResponse>> SendVoiceMessageAsync(UserAudioRequest request)
        {
            var response = new ServiceResponse<AIAudioResponse>();

            var session = await sessionRepository.GetByIdAsync(request.SessionId, request.UserId);
            if(session == null)
            {
                response.Success = false;
                response.Message = "Session Not Found or Unauthorized";
                return response;
            }

            // Save User Audio 
            string userAudioRelativePath = await fileStorageService.SaveFileAsync(request.Audio, request.UserId.ToString(), request.SessionId.ToString());
            string userAudioWebUrl = $"/{userAudioRelativePath}";

            // Save User Message to The Database 
            var userMessage = new ChatMessage
            {
                SessionId = request.SessionId,
                AudioUrl = userAudioRelativePath,
                Role = "user",
                Content = "Voice Note",
                CreatedAt = DateTime.Now
            };
            await messageRepository.AddAsync(userMessage);

            session.UpdatedAt = DateTime.Now;
            await sessionRepository.UpdateAsync(session);

            // Send The Audio to The AI (Streaming Directly From Memory For Better Performance) and Receives an AI Audio
            string aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
            string voicePath = configuration["AIService:VoicePath"] ?? "voice/ask-audio";

            string aiURL = $"{aiBaseURL.TrimEnd('/')}/{voicePath.TrimStart('/')}";

            AIAudioResponse? aiResponse = null;
            using (var multipartFormContent = new MultipartFormDataContent())
            {
                multipartFormContent.Add(new StringContent(request.SessionId.ToString()), "session_id");
                multipartFormContent.Add(new StringContent(request.UserId.ToString()), "user_id");

                //Stream The IFormFile Directly
                var fileStreamContent = new StreamContent(request.Audio.OpenReadStream());
                fileStreamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(request.Audio.ContentType);
                multipartFormContent.Add(fileStreamContent, name: "audio", fileName: request.Audio.FileName);

                try
                {
                    httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
                    var httpResponse = await httpClient.PostAsync(aiURL, multipartFormContent);

                    if (!httpResponse.IsSuccessStatusCode)
                    {
                        string errorBody = await httpResponse.Content.ReadAsStringAsync();
                        response.Success = false;
                        response.Message = $"AI Voice API Failed! Status: {httpResponse.StatusCode}. Details: {errorBody}";
                        return response;
                    }

                    aiResponse = await httpResponse.Content.ReadFromJsonAsync<AIAudioResponse>();
                }
                catch (Exception ex)
                {
                    response.Success = false;
                    response.Message = $"Failed to communicate with AI: {ex.Message}";
                    return response;
                }
            }


            // Download and Save AI Audio Response 
            string? finalAiAudioWebUrl = null;
            if (aiResponse != null && !string.IsNullOrEmpty(aiResponse.AudioUrl))
            {
                try
                {
                    Uri aiGeneratedUri = new Uri(aiResponse.AudioUrl);
                    string downloadableAudioUrl = $"{aiBaseURL.TrimEnd('/')}{aiGeneratedUri.PathAndQuery}";

                    // Download to Memory 
                    byte[] audioBytes = await httpClient.GetByteArrayAsync(downloadableAudioUrl);

                    // Save it in Uploads Folder
                    string aiAudioRelativePath = await fileStorageService.SaveFileAsync(audioBytes, "ai_response.wav", request.UserId.ToString(), request.SessionId.ToString()); ;
                    finalAiAudioWebUrl = $"/{aiAudioRelativePath}";

                    // Update the link for the mobile frontend
                    aiResponse.AudioUrl = $"{configuration["AppConfig:BaseURL"]}{finalAiAudioWebUrl}";
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to download AI audio: {ex.Message}");
                }
            }

            if(aiResponse != null)
            {
                var aiMessage = new ChatMessage
                {
                    SessionId = request.SessionId,
                    Role = "assistant",
                    Content = aiResponse.AnswerText ?? "No Response Generated.",
                    AudioUrl = finalAiAudioWebUrl,
                    CreatedAt = DateTime.Now,
                    ConfidenceScore = aiResponse.Confidence
                };

                if (aiResponse.Citations != null)
                {
                    foreach (var citation in aiResponse.Citations)
                    {
                        DocumentChunk chunk = await chunkRepository.GetByIdAsync(citation.ChunkId);
                        if (chunk != null) aiMessage.Chunks.Add(chunk);
                    }
                }

                await messageRepository.AddAsync(aiMessage);
            }

            response.Success = true;
            response.Data = aiResponse;
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
