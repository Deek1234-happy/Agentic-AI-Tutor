using System.ComponentModel.DataAnnotations;

namespace AgenticAITutor.Models.DTOs.Auth
{
    public class ResetPasswordRequestDto
    {
        public string? Email { get; set; }

        /// <summary>The 6-digit one-time password sent to the user's email.</summary>
        [RegularExpression(@"^\d{6}$", ErrorMessage = "OTP must be exactly 6 digits.")]
        public string? Otp { get; set; }

        public string? NewPassword { get; set; }
        public string? ConfirmNewPassword { get; set; }
    }
}
