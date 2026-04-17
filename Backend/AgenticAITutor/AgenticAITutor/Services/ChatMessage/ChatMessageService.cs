using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.DTOs.ChatMessage;
using AgenticAITutor.Repositories;
using Microsoft.AspNetCore.Http.HttpResults;
using System.Data;

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
            IHttpClientFactory httpClientFactory,
            IConfiguration configuration,
            IChatWebSourceRepository webSourceRepository,
            IFileStorageService fileStorageService)
        {
            this.messageRepository = messageRepository;
            this.sessionRepository = sessionRepository;
            this.chunkRepository = chunkRepository;
            this.httpClient = httpClientFactory.CreateClient(nameof(ChatMessageService)); ;
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
                //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
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
                foreach (var citation in aiResponse?.UsedChunks)
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

            var userMessage = new ChatMessage
            {
                SessionId = request.SessionId,
                Role = "user",
                Content = request.UserMessage ?? string.Empty,
                CreatedAt = DateTime.Now
            };
            await messageRepository.AddAsync(userMessage);


            session.UpdatedAt = DateTime.Now;
            await sessionRepository.UpdateAsync(session);


            string? aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
            string? webSearchPath = configuration["AIService:WebSearchPath"] ?? "searchweb";

            string? webSearchURL = $"{aiBaseURL.TrimEnd('/')}/{webSearchPath.TrimStart('/')}";


            WebSearchResponse? webSearchResponse = null;
            try
            {
                //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
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
                    ConfidenceScore = 0,
                    ChatWebSources = webSearchResponse.Sources.Select(s => new ChatWebSource
                    {
                        Domain = s.Domain,
                        Title = s.Title,
                        Url = s.URL
                    }).ToList()
                };

                await messageRepository.AddAsync(webSearchMessage);

            }
            response.Data = webSearchResponse;
            response.Success = true;
            return response;

        }

        //public async Task<ServiceResponse<AIAudioResponse>> SendVoiceMessageAsync(UserAudioRequest request)
        //{
        //    var response = new ServiceResponse<AIAudioResponse>();

        //    var session = await sessionRepository.GetByIdAsync(request.SessionId, request.UserId);
        //    if(session == null)
        //    {
        //        response.Success = false;
        //        response.Message = "Session Not Found or Unauthorized";
        //        return response;
        //    }

        //    if (request.Audio == null || request.Audio.Length == 0)
        //    {
        //        response.Success = false;
        //        response.Message = "The audio file is missing or empty.";
        //        return response;
        //    }

        //    // 1. Validate File Size (Maximum 10 MB)
        //    const long maxFileSize = 10 * 1024 * 1024;
        //    if (request.Audio.Length > maxFileSize)
        //    {
        //        response.Success = false;
        //        response.Message = "The audio file exceeds the maximum allowed size of 10 MB.";
        //        return response;
        //    }

        //    // 2. Validate File Extension and Content Type (MIME Type)
        //    var allowedExtensions = new[] { ".wav", ".mp3", ".m4a", ".ogg", ".flac" };
        //    var allowedMimeTypes = new[] { "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/x-m4a", "audio/flac", "audio/mp3" };

        //    var fileExtension = Path.GetExtension(request.Audio.FileName).ToLowerInvariant();
        //    var mimeType = request.Audio.ContentType.ToLowerInvariant();

        //    // Check if both the extension and the MIME type are valid audio formats
        //    if (!allowedExtensions.Contains(fileExtension) || !allowedMimeTypes.Contains(mimeType))
        //    {
        //        response.Success = false;
        //        response.Message = $"Invalid audio format. Allowed formats are: {string.Join(", ", allowedExtensions)}";
        //        return response;
        //    }

        //    // Save User Audio 
        //    string userAudioRelativePath = await fileStorageService.SaveFileAsync(request.Audio, request.UserId.ToString(), request.SessionId.ToString());
        //    string userAudioWebUrl = $"/{userAudioRelativePath}";

        //    // Save User Message to The Database 
        //    var userMessage = new ChatMessage
        //    {
        //        SessionId = request.SessionId,
        //        AudioUrl = userAudioRelativePath,
        //        Role = "user",
        //        Content = "Voice Note",
        //        CreatedAt = DateTime.Now
        //    };
        //    await messageRepository.AddAsync(userMessage);

        //    session.UpdatedAt = DateTime.Now;
        //    await sessionRepository.UpdateAsync(session);

        //    // Send The Audio to The AI (Streaming Directly From Memory For Better Performance) and Receives an AI Audio
        //    string aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
        //    string voicePath = configuration["AIService:VoicePath"] ?? "voice/ask-audio";

        //    string aiURL = $"{aiBaseURL.TrimEnd('/')}/{voicePath.TrimStart('/')}";

        //    AIAudioResponse? aiResponse = null;
        //    using (var multipartFormContent = new MultipartFormDataContent())
        //    {
        //        multipartFormContent.Add(new StringContent(request.SessionId.ToString()), "session_id");
        //        multipartFormContent.Add(new StringContent(request.UserId.ToString()), "user_id");

        //        //Stream The IFormFile Directly
        //        var fileStreamContent = new StreamContent(request.Audio.OpenReadStream());
        //        fileStreamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(request.Audio.ContentType);
        //        multipartFormContent.Add(fileStreamContent, name: "audio", fileName: request.Audio.FileName);

        //        try
        //        {
        //            httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
        //            var httpResponse = await httpClient.PostAsync(aiURL, multipartFormContent);

        //            if (!httpResponse.IsSuccessStatusCode)
        //            {
        //                string errorBody = await httpResponse.Content.ReadAsStringAsync();
        //                response.Success = false;
        //                response.Message = $"AI Voice API Failed! Status: {httpResponse.StatusCode}. Details: {errorBody}";
        //                return response;
        //            }

        //            aiResponse = await httpResponse.Content.ReadFromJsonAsync<AIAudioResponse>();
        //        }
        //        catch (Exception ex)
        //        {
        //            response.Success = false;
        //            response.Message = $"Failed to communicate with AI: {ex.Message}";
        //            return response;
        //        }
        //    }


        //    // Download and Save AI Audio Response 
        //    string? finalAiAudioWebUrl = null;
        //    if (aiResponse != null && !string.IsNullOrEmpty(aiResponse.AudioUrl))
        //    {
        //        try
        //        {
        //            Uri aiGeneratedUri = new Uri(aiResponse.AudioUrl);
        //            string downloadableAudioUrl = $"{aiBaseURL.TrimEnd('/')}{aiGeneratedUri.PathAndQuery}";

        //            // Download to Memory 
        //            byte[] audioBytes = await httpClient.GetByteArrayAsync(downloadableAudioUrl);

        //            // Save it in Uploads Folder
        //            string aiAudioRelativePath = await fileStorageService.SaveFileAsync(audioBytes, "ai_response.wav", request.UserId.ToString(), request.SessionId.ToString()); ;
        //            finalAiAudioWebUrl = $"/{aiAudioRelativePath}";

        //            // Update the link for the mobile frontend
        //            aiResponse.AudioUrl = $"{configuration["AppConfig:BaseURL"]}{finalAiAudioWebUrl}";
        //        }
        //        catch (Exception ex)
        //        {
        //            Console.WriteLine($"Failed to download AI audio: {ex.Message}");
        //        }
        //    }

        //    if(aiResponse != null)
        //    {
        //        var aiMessage = new ChatMessage
        //        {
        //            SessionId = request.SessionId,
        //            Role = "assistant",
        //            Content = aiResponse.AnswerText ?? "No Response Generated.", // What is The Different Between it and The Transcribtion to store just one of them 
        //            AudioUrl = finalAiAudioWebUrl,
        //            CreatedAt = DateTime.Now,
        //            ConfidenceScore = aiResponse.Confidence
        //        };

        //        if (aiResponse.Citations != null)
        //        {
        //            foreach (var citation in aiResponse.Citations)
        //            {
        //                DocumentChunk chunk = await chunkRepository.GetByIdAsync(citation.ChunkId);
        //                if (chunk != null) aiMessage.Chunks.Add(chunk);
        //            }
        //        }

        //        await messageRepository.AddAsync(aiMessage);
        //    }

        //    response.Success = true;
        //    response.Data = aiResponse;
        //    return response;

        //}

        public async Task<ServiceResponse<List<ChatMessageResponse>>> GetSessionMessagesAsync(Guid userId, Guid sessionId)
        {
            var response = new ServiceResponse<List<ChatMessageResponse>>();

            var session = await sessionRepository.GetByIdAsync(sessionId, userId);
            if (session == null)
            {
                response.Success = false;
                response.Message = "Session not found or unauthorized.";
                return response;
            }

            var messages = await messageRepository.GetBySessionIdAsync(sessionId);

            try
            {
                // LINQ Projection
                var messagesResponse = messages.Select(message => new ChatMessageResponse
                {
                    Id = message.Id,
                    SessionId = message.SessionId,
                    Role = message.Role,
                    Content = message.Content,
                    ConfidenceScore = message.ConfidenceScore,
                    AudioUrl = message.AudioUrl,
                    CreatedAt = message.CreatedAt,

                    // LINQ replaces the inner loop for Web Sources
                    WebSource = message.ChatWebSources?.Select(source => new WebSources
                    {
                        URL = source.Url,
                        Domain = source.Domain,
                        Title = source.Title
                    }).ToList() ?? new List<WebSources>(),

                    // LINQ replaces the inner loop for AI Citations
                    AICitation = message.Chunks?.Select(chunk => new AICitation
                    {
                        ChunkId = chunk.Id,
                        DocumentId = chunk.DocumentId,
                        PageStart = chunk.PageStart,
                        PageEnd = chunk.PageEnd
                    }).ToList() ?? new List<AICitation>()

                }).ToList();

                response.Data = messagesResponse;
                response.Success = true;
            }
            catch(Exception ex)
            {
                response.Success = false;
                response.Message = ex.Message;
            }


            
            return response;
        }


        public async Task<ServiceResponse<string>> SpeechToTextAsync(IFormFile audioFile)
        {
            var response = new ServiceResponse<string>();

            // 1. Validate File Size & Type
            if (audioFile == null || audioFile.Length == 0)
            {
                response.Success = false;
                response.Message = "The audio file is missing or empty.";
                return response;
            }

            const long maxFileSize = 10 * 1024 * 1024; // 10 MB
            if (audioFile.Length > maxFileSize)
            {
                response.Success = false;
                response.Message = "The audio file exceeds the maximum allowed size of 10 MB.";
                return response;
            }

            var allowedExtensions = new[] { ".wav", ".mp3", ".m4a", ".ogg", ".flac" };
            var allowedMimeTypes = new[] { "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/x-m4a", "audio/flac", "audio/mp3" };

            var fileExtension = Path.GetExtension(audioFile.FileName).ToLowerInvariant();
            var mimeType = audioFile.ContentType.ToLowerInvariant();

            if (!allowedExtensions.Contains(fileExtension) || !allowedMimeTypes.Contains(mimeType))
            {
                response.Success = false;
                response.Message = $"Invalid audio format. Allowed formats are: {string.Join(", ", allowedExtensions)}";
                return response;
            }

            // 2. Call Python STT
            string aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
            string sttPath = configuration["AIService:STTPath"] ?? "audio/stt";
            string sttURL = $"{aiBaseURL.TrimEnd('/')}/{sttPath.TrimStart('/')}";

            using (var multipartFormContent = new MultipartFormDataContent())
            {
                var fileStreamContent = new StreamContent(audioFile.OpenReadStream());
                fileStreamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(audioFile.ContentType);
                multipartFormContent.Add(fileStreamContent, name: "audio_file", fileName: audioFile.FileName);

                try
                {
                    //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
                    var sttHttpResponse = await httpClient.PostAsync(sttURL, multipartFormContent);

                    if (!sttHttpResponse.IsSuccessStatusCode)
                    {
                        string errorBody = await sttHttpResponse.Content.ReadAsStringAsync();
                        response.Success = false;
                        response.Message = $"Speech-to-Text API Failed. Status: {sttHttpResponse.StatusCode}. Details: {errorBody}";
                        return response;
                    }

                    var sttResult = await sttHttpResponse.Content.ReadFromJsonAsync<STTResponse>();

                    response.Data = sttResult?.Text ?? "Audio could not be transcribed.";
                    response.Success = true;
                }
                catch (Exception ex)
                {
                    response.Success = false;
                    response.Message = $"STT Communication Error: {ex.Message}";
                }
            }

            return response;
        }

        public async Task<ServiceResponse<string>> TextToSpeechAsync(Guid messageId, Guid userId)
        {
            var response = new ServiceResponse<string>();

            // 1. Fetch the message
            var message = await messageRepository.GetByIdAsync(messageId);
            if (message == null || message.Role != "assistant")
            {
                response.Success = false;
                response.Message = "Message not found or is not an AI response.";
                return response;
            }

            // 2. Security Check: Ensure the user actually owns the session this message belongs to!
            var session = await sessionRepository.GetByIdAsync(message.SessionId, userId);
            if (session == null)
            {
                response.Success = false;
                response.Message = "Unauthorized access to this message.";
                return response;
            }

            // 3. Cache Check: If we already generated audio for this, just return the existing link!
            if (!string.IsNullOrEmpty(message.AudioUrl))
            {
                response.Data = $"{configuration["AppConfig:BaseURL"]}{message.AudioUrl}";
                response.Success = true;
                return response;
            }

            // 4. Call Python TTS
            string aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";
            string ttsPath = configuration["AIService:TTSPath"] ?? "audio/tts";
            string ttsURL = $"{aiBaseURL.TrimEnd('/')}/{ttsPath.TrimStart('/')}";

            var ttsRequest = new TTSRequest { Text = message.Content };

            try
            {
                //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");
                var ttsHttpResponse = await httpClient.PostAsJsonAsync(ttsURL, ttsRequest);

                if (!ttsHttpResponse.IsSuccessStatusCode)
                {
                    string errorBody = await ttsHttpResponse.Content.ReadAsStringAsync();
                    response.Success = false;
                    response.Message = $"TTS API Failed. Status: {ttsHttpResponse.StatusCode}. Details: {errorBody}";
                    return response;
                }

                // Assuming Python returns the raw audio file bytes directly
                byte[] audioBytes = await ttsHttpResponse.Content.ReadAsByteArrayAsync();

                // Save locally using your FileStorageService
                string aiAudioRelativePath = await fileStorageService.SaveFileAsync(audioBytes, $"tts_{messageId}.wav", userId.ToString(), message.SessionId.ToString());

                // Update DB so we don't have to generate it again if they click play twice
                message.AudioUrl = $"{configuration["AppConfig:BaseURL"]}/{aiAudioRelativePath}";
                await messageRepository.UpdateAsync(message);

                response.Data = $"{message.AudioUrl}";
                response.Success = true;
            }
            catch (Exception ex)
            {
                response.Success = false;
                response.Message = $"TTS Generation Failed: {ex.Message}";
            }

            return response;
        }

    }
}
