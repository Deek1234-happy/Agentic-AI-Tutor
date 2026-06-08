using AgenticAITutor.Models.DTOs.Auth;

namespace AgenticAITutor.Services
{
    public interface IAuthService
    {
        Task<AuthResponse> RegisterAsync(RegisterRequest request);
        Task<AuthResponse> LoginAsync(LoginRequest request);
        Task<AgenticAITutor.Models.DTOs.ServiceResponse<string>> ForgotPasswordAsync(ForgotPasswordRequestDto request);
        Task<AgenticAITutor.Models.DTOs.ServiceResponse<string>> ResetPasswordAsync(ResetPasswordRequestDto request);
    }
}
