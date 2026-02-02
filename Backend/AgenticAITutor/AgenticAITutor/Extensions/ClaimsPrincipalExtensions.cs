using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;

namespace AgenticAITutor.Extensions
{
    public static class ClaimsPrincipalExtensions
    {
        public static Guid GetUserId(this ClaimsPrincipal user)
        {
            var id = user.FindFirst(JwtRegisteredClaimNames.Jti)?.Value;
            if(string.IsNullOrEmpty(id) )
                id = user.FindFirst(ClaimTypes.NameIdentifier)?.Value;
            return Guid.TryParse(id, out var parsedId) ? parsedId : Guid.Empty;
        }
    }
}
