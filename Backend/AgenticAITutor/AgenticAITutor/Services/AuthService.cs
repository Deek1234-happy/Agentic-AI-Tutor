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

            var user = new user
            {
                first_name = request.FirstName,
                last_name = request.LastName,
                email = request.Email.ToLower(),
                password_hash = passwordHasher.Hash(request.Password)
            };

            await userRepository.AddAsync(user);

            var jwtSecurityToken = CreateJwtToken(user);

            return new AuthResponse
            {
                Email = user.email,
                UserId = user.id,
                IsAuthenticated = true,
                Token = new JwtSecurityTokenHandler().WriteToken(jwtSecurityToken),
                ExpiresIn = jwtSecurityToken.ValidTo
            };
        }
        public async Task<AuthResponse> LoginAsync(LoginRequest request)
        {
            var authResponse = new AuthResponse();

            var user = await userRepository.GetByEmailAsync(request.Email.ToLower());

            if (user is null || !passwordHasher.Verify(request.Password,user.password_hash))
            { 
                authResponse.Message = "Email or Password is Incorrect"; 
                return authResponse;
            }

            var jwtSecurityToken = CreateJwtToken(user);

            authResponse.IsAuthenticated = true;
            authResponse.Email = user.email;
            authResponse.UserId = user.id;
            authResponse.Token = new JwtSecurityTokenHandler().WriteToken(jwtSecurityToken);
            authResponse.ExpiresIn = jwtSecurityToken.ValidTo;  



            return authResponse;
        }

        private JwtSecurityToken CreateJwtToken(user _user)
        {
            var claims = new[]
            {
                new Claim(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Email, _user.email),
                new Claim(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Jti, _user.id.ToString())
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
