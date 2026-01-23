using AgenticAITutor.Models.DTOs.Auth;

namespace AgenticAITutor.Services
{
    public interface IAuthService
    {
        Task<AuthResponse> RegisterAsync(RegisterRequest request);
        Task<AuthResponse> LoginAsync(LoginRequest request);
    }
}
