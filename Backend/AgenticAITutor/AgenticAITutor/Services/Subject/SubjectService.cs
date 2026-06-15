using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services
{
    public class SubjectService:ISubjectService
    {
        private readonly ISubjectRepository subjectRepository;
        private readonly HttpClient httpClient;
        private readonly IConfiguration configuration;
        private readonly IDocumentService documentService;

        public SubjectService(ISubjectRepository subjectRepository,
            IHttpClientFactory httpClientFactory,
            IConfiguration configuration,
            IDocumentService documentService)
        {
            this.subjectRepository = subjectRepository;
            this.httpClient = httpClientFactory.CreateClient(nameof(SubjectService));
            this.configuration = configuration;
            this.documentService = documentService;
        }

        public async Task<ServiceResponse<SubjectResponse>> AddAsync(SubjectRequest subjectRequest)
        {
            var response = new ServiceResponse<SubjectResponse>();


            Subject? subject = await subjectRepository.GetByNameAndUserAsync(subjectRequest);
            if (subject != null)
            {
                response.Success = false;
                response.Message = "Subject is Already Exists";
                return response;
            }

            subject = new Subject
            {
                Name = subjectRequest.Name.ToLower(),
                UserId = subjectRequest.UserId
            };
            await subjectRepository.AddAsync(subject);

            response.Success = true;
            response.Data = new SubjectResponse
            {
                Id = subject.Id,    
                UserId = subject.UserId,
                Name = subject.Name
            };

            return response;
        }

        public async Task<List<SubjectResponse>> GetAllAsync(Guid userId)
        {
            List<Subject> subjects = await subjectRepository.GetUserSubjectsAsync(userId);
            
            var subjectResponses = subjects.Select(subject => new SubjectResponse 
            {
                Id = subject.Id,
                UserId = subject.UserId,
                Name = subject.Name,
                Documents = subject.Documents.Select(document => new DocumentResponse
                {
                    Id = document.Id,
                    SubjectId = document.SubjectId,
                    UserId = document.UserId,
                    FileName = document.Filename,
                    FileType = document.FileType,
                    FileSize = document.FileSize,
                    UploadTime = document.UploadTime,
                    ProcessingStatus = document.ProcessingStatus,
                    KGStatus = document.KgStatus,
                    QuizChunkingStatus = document.QuizChunkingStatus,
                    StoragePath = document.StoragePath
                }).ToList()
            }).ToList();

            return subjectResponses;
        }
        public async Task<ServiceResponse<SubjectResponse?>> GetAsync(Guid subjectId, Guid userId)
        {
            var response = new ServiceResponse<SubjectResponse?>();

            Subject? subject = await subjectRepository.GetByIdAsync(subjectId);
            if (subject != null && subject.UserId == userId)
            {
                response.Success = true;
                response.Data = new SubjectResponse
                {
                    Id = subject.Id,
                    UserId = subject.UserId,
                    Name = subject.Name,
                    Documents = subject.Documents.Select(document => new DocumentResponse
                    {
                        Id = document.Id,
                        SubjectId = document.SubjectId,
                        UserId = document.UserId,
                        FileName = document.Filename,
                        FileType = document.FileType,
                        FileSize = document.FileSize,
                        UploadTime = document.UploadTime,
                        ProcessingStatus = document.ProcessingStatus,
                        KGStatus = document.KgStatus,
                        QuizChunkingStatus = document.QuizChunkingStatus,
                        StoragePath = document.StoragePath,

                    }).ToList()
                };
                return response;
            }

            response.Success = false;
            response.Message = "Subject Not Found";
            return response;
        }
        public async Task<ServiceResponse<string>> DeleteAsync(Guid subjectId, Guid userId)
        {
            var response = new ServiceResponse<string>();
            Subject? subject = await subjectRepository.GetByIdAsync(subjectId);

            if (subject == null || subject.UserId != userId)
            {
                response.Success = false;
                response.Message = "Subject Not Found";
                return response;
            }

            // Notify the AI service to delete the knowledge graph data for this subject
            try
            {
                var aiBaseUrl = configuration["AIService:BaseURL"];
                var kgSubjectDeletePath = configuration["AIService:KGSubjectDeletePath"];
                var kgDeleteUrl = $"{aiBaseUrl}/{kgSubjectDeletePath}/{subjectId}?user_id={userId}";
                await httpClient.DeleteAsync(kgDeleteUrl);
            }
            catch
            {
                // Log and continue — KG cleanup failure should not block the subject deletion
            }

            // Since the database enforces ON DELETE CASCADE and SubjectId cannot be null,
            // we must explicitly delete the documents through the DocumentService BEFORE deleting the subject.
            // This ensures that physical files (wwwroot/uploads) and AI Knowledge Graph data are properly cleaned up,
            // preventing massive data leaks that would happen if we just let the DB silently cascade the delete.
            var documents = await documentService.GetDocumentsBySubjectAsync(userId, subjectId);
            foreach(var doc in documents)
            {
                await documentService.DeleteDocumentAsync(doc.Id, userId);
            }

            await subjectRepository.DeleteAsync(subject);
            response.Success = true;
            response.Message = "Subject Deleted Successfully";
            return response;
        }
        public async Task<ServiceResponse<string>> UpdateAsync(Guid subjectId, SubjectRequest subjectRequest)
        {
            var response = new ServiceResponse<string>();

            Subject? subject = await subjectRepository.GetByIdAsync(subjectId);
            if (subject == null || subject.UserId != subjectRequest.UserId)
            { 
                response.Success = false;
                response.Message = "Subject Not Found";
                return response; 
            }
            if (!string.Equals(subject.Name, subjectRequest.Name, StringComparison.CurrentCultureIgnoreCase))
            {
                // Only check DB if the name is actually changing
                var duplicateCheck = await subjectRepository.GetByNameAndUserAsync(subjectRequest);

                // Ensure we aren't detecting the current record as a duplicate (though the Name check above handles most cases)
                if (duplicateCheck != null && duplicateCheck.Id != subjectId)
                {
                    response.Success = false;
                    response.Message = "Subject name already exists.";
                    return response;
                }
            }

            subject.Name = subjectRequest.Name.ToLower();
            await subjectRepository.UpdateAsync(subject);

            response.Success = true;
            response.Message = "Subject Updated Successfully";

            return response;
        }

        public async Task<ServiceResponse<List<DocumentDropdownResponse>>> GetDocumentsForDropdownAsync(Guid subjectId, Guid userId)
        {
            var response = new ServiceResponse<List<DocumentDropdownResponse>>();
            
            Subject? subject = await subjectRepository.GetByIdAsync(subjectId);
            if (subject == null || subject.UserId != userId)
            {
                response.Success = false;
                response.Message = "Subject Not Found";
                return response;
            }

            response.Success = true;
            response.Data = subject.Documents.Select(doc => new DocumentDropdownResponse
            {
                Id = doc.Id,
                FileName = doc.Filename
            }).ToList();

            return response;
        }


    }
}
