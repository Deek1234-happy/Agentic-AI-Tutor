using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface ISubjectService
    {
        Task<string> AddAsync(SubjectModel subjectModel);
        Task<List<Subject?>> GetAllAsync(Guid userId);
        Task<Subject?> GetAsync(Guid subjectId, Guid userId);
        Task<ServiceResponse<string>> DeleteAsync(Guid subjectId, Guid userId);
        Task<ServiceResponse<string>> UpdateAsync(Guid subjectId, SubjectModel subjectModel);
    }
}
