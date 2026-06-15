using AgenticAITutor.Helpers;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.DTOs.Auth;
using AgenticAITutor.Repositories;
using Hangfire;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;

namespace AgenticAITutor.Services
{
    public class AuthService : IAuthService
    {
        private readonly IUserRepository userRepository;
        private readonly IPasswordHasher passwordHasher;
        private readonly IBackgroundJobClient backgroundJobClient;
        private readonly ILogger<AuthService> logger;
        private readonly JWT jwt;

        public AuthService(
            IUserRepository userRepository,
            IOptions<JWT> jwt,
            IPasswordHasher passwordHasher,
            IBackgroundJobClient backgroundJobClient,
            ILogger<AuthService> logger)
        {
            this.userRepository = userRepository;
            this.passwordHasher = passwordHasher;
            this.backgroundJobClient = backgroundJobClient;
            this.logger = logger;
            this.jwt = jwt.Value;
        }
        public async Task<AuthResponse> RegisterAsync(RegisterRequest request)
        {


            if (await userRepository.GetByEmailAsync(request.Email.ToLower()) is not null)
                return new AuthResponse { Message = "Email is Already Registered!" };

            var user = new User
            {
                FirstName = request.FirstName,
                LastName = request.LastName,
                Email = request.Email.ToLower(),
                PasswordHash = passwordHasher.Hash(request.Password)
            };

            await userRepository.AddAsync(user);

            var jwtSecurityToken = CreateJwtToken(user);

            return new AuthResponse
            {
                Email = user.Email,
                UserId = user.Id,
                IsAuthenticated = true,
                Token = new JwtSecurityTokenHandler().WriteToken(jwtSecurityToken),
                ExpiresIn = jwtSecurityToken.ValidTo
            };
        }
        public async Task<AuthResponse> LoginAsync(LoginRequest request)
        {
            var authResponse = new AuthResponse();

            var user = await userRepository.GetByEmailAsync(request.Email.ToLower());

            if (user is null || !passwordHasher.Verify(request.Password,user.PasswordHash))
            { 
                authResponse.Message = "Email or Password is Incorrect"; 
                return authResponse;
            }

            user.LastLogin = DateTime.Now;
            await userRepository.UpdateAsync(user);

            var jwtSecurityToken = CreateJwtToken(user);

            authResponse.IsAuthenticated = true;
            authResponse.Email = user.Email;
            authResponse.UserId = user.Id;
            authResponse.Token = new JwtSecurityTokenHandler().WriteToken(jwtSecurityToken);
            authResponse.ExpiresIn = jwtSecurityToken.ValidTo;  



            return authResponse;
        }

        public async Task<ServiceResponse<string>> ForgotPasswordAsync(ForgotPasswordRequestDto request)
        {
            const string genericMessage =
                "If an account exists for this email, a password reset message has been sent.";

            try
            {
                var normalizedEmail = request.Email!.Trim().ToLowerInvariant();
                var user = await userRepository.GetByEmailAsync(normalizedEmail);

                if (user == null)
                    return new ServiceResponse<string> { Message = genericMessage };

                var otp = GenerateOtp();
                user.PasswordResetOtp = otp;
                user.OtpExpiryTime = DateTime.Now.AddMinutes(15);
                await userRepository.UpdateAsync(user);

                backgroundJobClient.Enqueue<IEmailService>(
                    emailService => emailService.SendPasswordResetEmailAsync(user.Email, otp));
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Failed to process forgot-password request.");
            }

            return new ServiceResponse<string> { Message = genericMessage };
        }

        public async Task<ServiceResponse<string>> ResetPasswordAsync(ResetPasswordRequestDto request)
        {
            var normalizedEmail = request.Email!.Trim().ToLowerInvariant();
            var user = await userRepository.GetByEmailAsync(normalizedEmail);

            if (user == null ||
                string.IsNullOrWhiteSpace(user.PasswordResetOtp) ||
                user.OtpExpiryTime == null ||
                user.OtpExpiryTime <= DateTime.Now ||
                !OtpMatches(user.PasswordResetOtp, request.Otp!))
            {
                return new ServiceResponse<string>
                {
                    Success = false,
                    Message = "The OTP is invalid or has expired."
                };
            }

            user.PasswordHash = passwordHasher.Hash(request.NewPassword!);
            user.PasswordResetOtp = null;
            user.OtpExpiryTime = null;
            await userRepository.UpdateAsync(user);

            return new ServiceResponse<string>
            {
                Message = "Password has been reset successfully."
            };
        }

        public async Task<ServiceResponse<string>> ChangePasswordAsync(Guid userId, ChangePasswordRequestDto request)
        {
            var user = await userRepository.GetByIdAsync(userId);
            if (user == null)
            {
                return new ServiceResponse<string>
                {
                    Success = false,
                    Message = "User not found."
                };
            }

            if (!passwordHasher.Verify(request.OldPassword!, user.PasswordHash))
            {
                return new ServiceResponse<string>
                {
                    Success = false,
                    Message = "Incorrect old password."
                };
            }

            user.PasswordHash = passwordHasher.Hash(request.NewPassword!);
            await userRepository.UpdateAsync(user);

            return new ServiceResponse<string>
            {
                Message = "Password has been changed successfully."
            };
        }

        /// <summary>
        /// Generates a cryptographically secure random 6-digit OTP string (e.g. "482015").
        /// </summary>
        private static string GenerateOtp()
        {
            // Use RandomNumberGenerator to obtain an unbiased value in [0, 1_000_000)
            var value = RandomNumberGenerator.GetInt32(0, 1_000_000);
            return value.ToString("D6");
        }

        /// <summary>
        /// Constant-time OTP comparison to prevent timing attacks.
        /// </summary>
        private static bool OtpMatches(string storedOtp, string suppliedOtp)
        {
            var storedBytes  = System.Text.Encoding.UTF8.GetBytes(storedOtp);
            var suppliedBytes = System.Text.Encoding.UTF8.GetBytes(suppliedOtp);

            return storedBytes.Length == suppliedBytes.Length &&
                   CryptographicOperations.FixedTimeEquals(storedBytes, suppliedBytes);
        }

        private JwtSecurityToken CreateJwtToken(User user)
        {
            var claims = new[]
            {
                new Claim(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Email, user.Email),
                new Claim(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Jti, user.Id.ToString())
            };

            var symmetricSecurityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwt.Key));
            var signingCredentials = new SigningCredentials(symmetricSecurityKey, SecurityAlgorithms.HmacSha256);

            var jwtSecurityToken = new JwtSecurityToken(
                issuer: jwt.Issuer,
                audience: jwt.Audience,
                claims: claims,
                expires: DateTime.Now.AddDays(jwt.DurationInDays),
                signingCredentials: signingCredentials
                );

            return jwtSecurityToken;
        }

    }
}
