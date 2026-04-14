using AgenticAITutor.Data;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Conventions;

namespace AgenticAITutor.Repositories
{
    public class SubjectRepository:ISubjectRepository
    {
        private readonly AppDbContext dbContext;

        public SubjectRepository(AppDbContext dbContext)
        {
            this.dbContext = dbContext;
        }

        public async Task AddAsync(Subject subject)
        {
            await dbContext.Subjects.AddAsync(subject);
            await dbContext.SaveChangesAsync();
        }

        public async Task<Subject?> GetByIdAsync(Guid id)
        {
            return await dbContext.Subjects.Include(s => s.Documents).FirstOrDefaultAsync(s => s.Id == id);
        }
        public async Task<Subject?> GetByNameAndUserAsync(SubjectRequest subjectModel)
        {
            return await dbContext.Subjects.FirstOrDefaultAsync(s => s.Name.ToLower() ==  subjectModel.Name.ToLower() && s.UserId == subjectModel.UserId);
        }

        public async Task DeleteAsync(Subject subject)
        {
            dbContext.Subjects.Remove(subject);
            await dbContext.SaveChangesAsync();
        }
        public async Task UpdateAsync(Subject subject)
        {
            dbContext.Subjects.Update(subject);
            await dbContext.SaveChangesAsync();
        }

        public async Task<List<Subject>> GetUserSubjectsAsync(Guid userId)
        {
            List<Subject> subjects = await dbContext.Subjects.Include(s => s.Documents).Where(s => s.UserId == userId).ToListAsync();
            return subjects;
        }
    }
}
