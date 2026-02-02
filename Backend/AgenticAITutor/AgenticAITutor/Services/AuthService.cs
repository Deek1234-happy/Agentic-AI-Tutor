using AgenticAITutor.Helpers;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs.Auth;
using AgenticAITutor.Repositories;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;

namespace AgenticAITutor.Services
{
    public class AuthService : IAuthService
    {
        private readonly IUserRepository userRepository;
        private readonly IPasswordHasher passwordHasher;
        private readonly JWT jwt;

        public AuthService(IUserRepository userRepository, IOptions<JWT> jwt, IPasswordHasher passwordHasher)
        {
            this.userRepository = userRepository;
            this.passwordHasher = passwordHasher;
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
