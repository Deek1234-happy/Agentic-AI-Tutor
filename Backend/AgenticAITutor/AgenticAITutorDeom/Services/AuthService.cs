using AgenticAITutorDeom.Helpers;
using AgenticAITutorDeom.Models;
using AgenticAITutorDeom.Models.DTOs.Auth;
using AgenticAITutorDeom.Repositories;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;

namespace AgenticAITutorDeom.Services
{
    public class AuthService : IAuthService
    {
        private readonly IUserRepository userRepository;
        private readonly JWT jwt;

        public AuthService(IUserRepository userRepository, IOptions<JWT> jwt)
        {
            this.userRepository = userRepository;
            this.jwt = jwt.Value;
        }
        public async Task<AuthResponse> RegisterAsync(RegisterRequest request)
        {
            if (await userRepository.GetByEmailAsync(request.Email) is not null)
                return new AuthResponse { Message = "Email is Already Registered!" };

            var user = new user
            {
                first_name = request.FirstName,
                last_name = request.LastName,
                email = request.Email,
                password_hash = request.Password // The Password Will Be Hashed Later and Put Data Annotation on Password
            };

            await userRepository.AddAsync(user);

            var jwtSecurityToken = await CreateJwtToken(user);

            return new AuthResponse
            {
                Email = user.email,
                UserId = user.id,
                IsAuthenticated = true,
                Token = new JwtSecurityTokenHandler().WriteToken(jwtSecurityToken),
                ExpiresIn = jwtSecurityToken.ValidTo
            };
        }
        public Task<AuthResponse> LoginAsync(LoginRequest request)
        {
            throw new NotImplementedException();
        }

        private async Task<JwtSecurityToken> CreateJwtToken(user _user)
        {
            var claims = new[]
            {
                new Claim(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Email, _user.email),
                new Claim(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Jti, _user.id.ToString())
            };

            var symmetricSecurityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwt.Key));
            var signingCredentials = new SigningCredentials(symmetricSecurityKey, SecurityAlgorithms.HmacSha256);

            var jwtSecurityToken = new JwtSecurityToken(
                issuer : jwt.Issuer,
                audience: jwt.Audience,
                claims:claims,
                expires:DateTime.Now.AddDays(jwt.DurationInDays),
                signingCredentials: signingCredentials
                );

            return jwtSecurityToken;
        }

    }
}
