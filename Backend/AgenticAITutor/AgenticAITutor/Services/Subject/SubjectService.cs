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
            if (subject != null)
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
        public async Task<Subject?> GetAsync(Guid subjectId, Guid userId)
        {
            Subject? subject = await subjectRepository.GetByIdAsync(subjectId);

            if (subject != null && subject.UserId == userId)
                return subject;

            return null;
        }
        public async Task<ServiceResponse<string>> DeleteAsync(Guid subjectId, Guid userId)
        {
            var response = new ServiceResponse<string>();
            Subject? subject = await GetAsync(subjectId, userId);

            if (subject == null)
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
        public async Task<ServiceResponse<string>> UpdateAsync(Guid subjectId, SubjectModel subjectModel)
        {
            var response = new ServiceResponse<string>();

            Subject? subject = await GetAsync(subjectId, subjectModel.UserId);
            if (subject == null)
            { 
                response.Success = false;
                response.Message = "Subject Not Found";
                return response; 
            }
            if (!string.Equals(subject.Name, subjectModel.Name, StringComparison.CurrentCultureIgnoreCase))
            {
                // Only check DB if the name is actually changing
                var duplicateCheck = await subjectRepository.GetByNameAndUserAsync(subjectModel);

                // Ensure we aren't detecting the current record as a duplicate (though the Name check above handles most cases)
                if (duplicateCheck != null && duplicateCheck.Id != subjectId)
                {
                    response.Success = false;
                    response.Message = "Subject name already exists.";
                    return response;
                }
            }

            subject.Name = subjectModel.Name.ToLower();
            await subjectRepository.UpdateAsync(subject);

            response.Success = true;
            response.Message = "Subject Updated Successfully";

            return response;
        }


    }
}
