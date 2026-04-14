using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services
{
    public class SubjectService:ISubjectService
    {
        private readonly ISubjectRepository subjectRepository;

        public SubjectService(ISubjectRepository subjectRepository)
        {
            this.subjectRepository = subjectRepository;
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


    }
}
