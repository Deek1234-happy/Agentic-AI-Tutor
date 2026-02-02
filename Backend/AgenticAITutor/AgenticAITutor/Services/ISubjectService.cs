using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface ISubjectService
    {
        Task<string> AddAsync(SubjectModel subjectModel);
        Task<List<Subject?>> GetAllAsync(Guid userId);
        Task<Subject?> GetAsync(SubjectModel subjectModel);
        Task<string> DeleteAsync(SubjectModel subjectModel);
        Task<string> UpdateAsync(string oldName, string newName, Guid id);
    }
}
