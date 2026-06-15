using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IUserService
    {
        Task<ServiceResponse<UserResponse>> GetByIdAsync(Guid id);
        Task<ServiceResponse<UserResponse>> UpdateAsync(Guid id, UserUpdateRequest request);
        Task<ServiceResponse<bool>> DeleteAsync(Guid id);

    }
}
