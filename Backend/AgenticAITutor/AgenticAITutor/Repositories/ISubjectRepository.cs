using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Repositories
{
    public interface ISubjectRepository
    {
        Task AddAsync(Subject subject);
        Task<Subject?> GetByIdAsync(Guid id);
        Task<Subject?> GetByNameAndUserAsync(SubjectModel subjectModel);
        Task DeleteByIdAsync(Guid id);
        Task DeleteByNameAndUserAsync(SubjectModel subjectModel);
        Task UpdateAsync(Subject subject);
        Task<List<Subject>> GetUserSubjectsAsync(Guid userId);
    }
}
