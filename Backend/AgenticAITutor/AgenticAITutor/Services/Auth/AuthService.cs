using AgenticAITutor.Helpers;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.DTOs.Auth;
using AgenticAITutor.Repositories;
using Hangfire;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
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

                var resetToken = GenerateSecureResetToken();
                user.ResetPasswordToken = resetToken;
                user.ResetPasswordTokenExpiry = DateTime.Now.AddMinutes(15);
                await userRepository.UpdateAsync(user);

                backgroundJobClient.Enqueue<IEmailService>(
                    emailService => emailService.SendPasswordResetEmailAsync(user.Email, resetToken));
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
                string.IsNullOrWhiteSpace(user.ResetPasswordToken) ||
                user.ResetPasswordTokenExpiry == null ||
                user.ResetPasswordTokenExpiry <= DateTime.Now ||
                !TokenMatches(user.ResetPasswordToken, request.Token!))
            {
                return new ServiceResponse<string>
                {
                    Success = false,
                    Message = "The password reset token is invalid or has expired."
                };
            }

            user.PasswordHash = passwordHasher.Hash(request.NewPassword!);
            user.ResetPasswordToken = null;
            user.ResetPasswordTokenExpiry = null;
            await userRepository.UpdateAsync(user);

            return new ServiceResponse<string>
            {
                Message = "Password has been reset successfully."
            };
        }

        private static string GenerateSecureResetToken()
        {
            return Base64UrlEncoder.Encode(RandomNumberGenerator.GetBytes(32));
        }

        private static bool TokenMatches(string storedToken, string suppliedToken)
        {
            var storedBytes = Encoding.UTF8.GetBytes(storedToken);
            var suppliedBytes = Encoding.UTF8.GetBytes(suppliedToken);

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
