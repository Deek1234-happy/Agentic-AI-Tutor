using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Repositories
{
    public interface ISubjectRepository
    {
        Task AddAsync(Subject subject);
        Task DeleteAsync(Subject subject);
        Task UpdateAsync(Subject subject);
        Task<Subject?> GetByIdAsync(Guid id);
        Task<Subject?> GetByNameAndUserAsync(SubjectRequest subjectModel);
        Task<List<Subject>> GetUserSubjectsAsync(Guid userId);
    }
}
