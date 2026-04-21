using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface ISubjectService
    {
        Task<ServiceResponse<SubjectResponse>> AddAsync(SubjectRequest subjectRequest);
        Task<List<SubjectResponse>> GetAllAsync(Guid userId);
        Task<ServiceResponse<SubjectResponse?>> GetAsync(Guid subjectId, Guid userId);
        Task<ServiceResponse<string>> DeleteAsync(Guid subjectId, Guid userId);
        Task<ServiceResponse<string>> UpdateAsync(Guid subjectId, SubjectRequest subjectModel);
        Task<ServiceResponse<List<DocumentDropdownResponse>>> GetDocumentsForDropdownAsync(Guid subjectId, Guid userId);
    }
}
