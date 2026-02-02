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

        public async Task<string> AddAsync(SubjectModel subjectModel)
        {
            Subject? subject = await subjectRepository.GetByNameAndUserAsync(subjectModel);
            if (subject != null && subject.UserId == subjectModel.UserId)
                return "Subject is Already Exists";

            subject = new Subject
            {
                Name = subjectModel.Name.ToLower(),
                UserId = subjectModel.UserId
            };
            await subjectRepository.AddAsync(subject);
            return "Subject Added Sccessfully";
        }

        public async Task<List<Subject?>> GetAllAsync(Guid userId)
        {
            List<Subject> subjects = await subjectRepository.GetUserSubjectsAsync(userId);
            return subjects;
        }
        public async Task<Subject?> GetAsync(SubjectModel subjectModel)
        {
            Subject? subject = await subjectRepository.GetByNameAndUserAsync(subjectModel);
            if (subject != null && subject.UserId == subjectModel.UserId)
                return subject;

            return null;
        }
        public async Task<string> DeleteAsync(SubjectModel subjectModel)
        {
            Subject? subject = await GetAsync(subjectModel);
            if (subject == null)
                return "There is no Subject With This Name";
            await subjectRepository.DeleteByNameAndUserAsync(subjectModel);
            return "Subject Deleted Succefully";
        }
        public async Task<string> UpdateAsync(string oldName, string newName, Guid id)
        {
            SubjectModel subjectModel = new SubjectModel
            {
                Name = oldName,
                UserId = id
            };
            Subject? subject = await GetAsync(subjectModel);
            if (subject == null)
                return "There is no Subject With This Name";
            subjectModel.Name = newName;
            subject = await GetAsync(subjectModel);
            if (subject != null)
                return "You already have a subject with that new name";

            subjectModel.Name = oldName;
            subject = await GetAsync(subjectModel);
            subject.Name = newName;

            await subjectRepository.UpdateAsync(subject);
            return "Subject Updated Succefully";
        }


    }
}
