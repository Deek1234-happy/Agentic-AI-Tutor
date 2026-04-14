using AgenticAITutor.Models.DTOs.Auth;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly IAuthService authService;

        public AuthController(IAuthService authService)
        {
            this.authService = authService;
        }

        /// <summary> Register a New User Account </summary>
        /// <remarks> Returns a JWT Token on Success</remarks>
        /// <response code="200">Registration successful — returns JWT token</response>
        /// <response code="400">Email already exists or validation failed</response>
        [HttpPost("register")]
        [ProducesResponseType<AuthResponse>(200)]
        [ProducesResponseType<string>(400)]
        public async Task<IActionResult> RegisterAsync([FromBody]RegisterRequest request)
        {
            var result = await authService.RegisterAsync(request);

            if(!result.IsAuthenticated)
                return BadRequest(result.Message);

            return Ok(result);
        }

        /// <summary> Login With Existing Credentials </summary>
        /// <remarks> Returns a JWT Token on Success</remarks>
        /// <response code="200">Login successful — returns JWT token</response>
        /// <response code="400">Invalid email or password</response>
        [HttpPost("login")]
        [ProducesResponseType<AuthResponse>(200)]
        [ProducesResponseType<string>(400)]
        public async Task<IActionResult> LoginAsync([FromBody] LoginRequest request)
        {
            var result = await authService.LoginAsync(request);

            if (!result.IsAuthenticated)
                return BadRequest(result.Message);

            return Ok(result);
        }
    }
}
