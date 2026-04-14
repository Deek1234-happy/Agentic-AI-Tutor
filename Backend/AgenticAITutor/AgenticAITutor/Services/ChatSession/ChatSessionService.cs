using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services
{
    public class ChatSessionService : IChatSessionService
    {
        private readonly IChatSessionRepository chatSessionRepository;
        private readonly IDocumentRepository documentRepository;

        public ChatSessionService(IChatSessionRepository chatSessionRepository, IDocumentRepository documentRepository)
        {
            this.chatSessionRepository = chatSessionRepository;
            this.documentRepository = documentRepository;
        }

        public async Task<ServiceResponse<ChatSessionResponse>> CreateSessionAsync(ChatSessionRequest request)
        {
            var response = new ServiceResponse<ChatSessionResponse>();

            var selectedDocs = new List<Document>();
            if(request.DocumentIds != null && request.DocumentIds.Count > 0)
            {
                selectedDocs = await documentRepository.GetDocumentsByIdsAsync(request.DocumentIds, request.UserId);
                if(selectedDocs.Count != request.DocumentIds.Count)
                {
                    response.Success = false;
                    response.Message = "One or More Documents Were Not Found or Don't Belong To You.";
                    return response;
                }

            }
                var chatSession = new ChatSession()
                {
                    UserId = request.UserId,
                    Title = "New Chat",
                    StartedAt = DateTime.Now,
                    UpdatedAt = DateTime.Now,
                    Documents = selectedDocs
                };

                await chatSessionRepository.AddAsync(chatSession);

                response.Data = new ChatSessionResponse()
                {
                    Id = chatSession.Id,
                    Title = chatSession.Title,
                    StartedAt = chatSession.StartedAt,
                    UpdatedAt = chatSession.UpdatedAt,
                    NumberOfDocuments = chatSession.Documents.Count,
                    Documents = chatSession.Documents.Select(document => new DocumentResponse
                    {
                        Id = document.Id,
                        SubjectId = document.SubjectId,
                        UserId = document.UserId,
                        FileName = document.Filename,
                        FileType = document.FileType,
                        FileSize = document.FileSize,
                        UploadTime = document.UploadTime,
                        ProcessingStatus = document.ProcessingStatus,
                        StoragePath = document.StoragePath
                    }).ToList()
                };

                response.Success = true;
                return response;

        }

        public async Task<ServiceResponse<bool>> DeleteSessionAsync(Guid userId, Guid sessioId)
        {
            var response = new ServiceResponse<bool>();

            ChatSession? session = await chatSessionRepository.GetByIdAsync(sessioId, userId);
            
            if(session == null)
            {
                response.Success = false;
                response.Message = "Chat Session Not Found";
                return response; 
            }

            await chatSessionRepository.DeleteAsync(session);

            response.Success = true;
            response.Data = true;
            response.Message = "Chat Session Deleted Successfully";

            return response;
        }
        public async Task<ServiceResponse<bool>> UpdateSessionAsync(ChatSessionUpdate request)
        {
            var response = new ServiceResponse<bool>();

            ChatSession? session = await chatSessionRepository.GetByIdAsync(request.SessionId, request.UserId);

            if (session == null)
            {
                response.Success = false;
                response.Message = "Chat Session Not Found";
                return response;
            }

            session.Title = request.Title;
            session.UpdatedAt = DateTime.Now;

            await chatSessionRepository.UpdateAsync(session);

            response.Success = true;
            response.Data = true;
            response.Message = "Chat Title Updated Successfully";

            return response;
        }

        public async Task<ServiceResponse<List<ChatSessionResponse>>> GetUserSessionsAsync(Guid userId)
        {
            var sessions = await chatSessionRepository.GetAllAsync(userId);

            var dtos = sessions.Select(s => new ChatSessionResponse
            {
                Id = s.Id,
                Title = s.Title,
                StartedAt = s.StartedAt,
                UpdatedAt = s.UpdatedAt,
                NumberOfDocuments = s.Documents.Count,
                Documents = s.Documents.Select(document => new DocumentResponse
                {
                    Id = document.Id,
                    SubjectId = document.SubjectId,
                    UserId = document.UserId,
                    FileName = document.Filename,
                    FileType = document.FileType,
                    FileSize = document.FileSize,
                    UploadTime = document.UploadTime,
                    ProcessingStatus = document.ProcessingStatus,
                    StoragePath = document.StoragePath
                }).ToList()
            }).ToList();

            var response = new ServiceResponse<List<ChatSessionResponse>>
            {
                Data = dtos,
                Success = true
            };

            return response;
        }

    }
}
