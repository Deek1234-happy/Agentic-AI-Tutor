using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services
{
    public class UserService : IUserService
    {
        private readonly IUserRepository userRepository;

        public UserService(IUserRepository userRepository)
        {
            this.userRepository = userRepository;
        }
        public async Task<ServiceResponse<UserResponse>> GetByIdAsync(Guid id)
        {
            var response = new ServiceResponse<UserResponse>();

            var user = await userRepository.GetByIdAsync(id);
            if (user == null)
            {
                response.Success = false;
                response.Message = "User Not Found";
                return response;
            }

            var stats = await userRepository.GetStatsAsync(id);

            response.Data = new UserResponse
            {
                Id = id,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Email = user.Email,
                CreatedDate = user.CreatedAt,
                NumberOfDocuments = stats.DocumentCount,
                NumberOfSubjects = stats.SubjectCount,
                NumberOfQuizzes = stats.QuizCount
            };

            response.Success = true;
            return response;
        }

        public async Task<ServiceResponse<UserResponse>> UpdateAsync(Guid id, UserUpdateRequest request)
        {
            var response = new ServiceResponse<UserResponse>();

            var user = await userRepository.GetByIdAsync(id);
            if (user == null)
            {
                response.Success = false;
                response.Message = "User Not Found";
                return response;
            }

            if(request?.Email != null && user.Email.ToLower() != request?.Email?.ToLower())
            {
                var emailExist = await userRepository.GetByEmailAsync(request?.Email?.ToLower());
                if (emailExist != null)
                {
                    response.Success = false;
                    response.Message = "This email is already taken by another account.";
                    return response;
                }
            }

            user.FirstName = request?.FirstName??user.FirstName;
            user.LastName = request?.LastName??user.LastName;
            user.Email = request?.Email ?? user.Email;

            await userRepository.UpdateAsync(user); 
            return await GetByIdAsync(id);


        }
        public async Task<ServiceResponse<bool>> DeleteAsync(Guid id)
        {
            var response = new ServiceResponse<bool>();

            var user = await userRepository.GetByIdAsync(id);
            if (user == null)
            {
                response.Success = false;
                response.Message = "User not found.";
                return response;
            }

            await userRepository.DeleteAsync(user);

            response.Data = true;
            response.Success = true;
            response.Message = "Account Deleted Successfully";

            return response;
        }


    }
}
