namespace AgenticAITutor.Models.DTOs.Auth
{
    public class ChangePasswordRequestDto
    {
        public string? OldPassword { get; set; }
        public string? NewPassword { get; set; }
        public string? ConfirmNewPassword { get; set; }
    }
}
