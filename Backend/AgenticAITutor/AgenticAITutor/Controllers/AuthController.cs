using AgenticAITutor.Extensions;
using AgenticAITutor.Models.DTOs.Auth;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Authorization;
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
        /// <remarks> 
        /// Creates a new user in the database and returns a JWT Token.
        /// **Required Fields:** `FirstName`, `LastName`, `Email`, `Password`.
        /// Passwords must match and follow security standards (e.g., minimum length).
        /// </remarks>
        /// <param name="request">The user registration details</param>
        /// <response code="200">Registration successful — returns AuthResponse containing the JWT token</response>
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
        /// <remarks> 
        /// Authenticates the user and returns a JWT Token on Success.
        /// The JWT Token must be included in the `Authorization: Bearer {token}` header for all secured endpoints.
        /// </remarks>
        /// <param name="request">The user's login credentials (Email and Password)</param>
        /// <response code="200">Login successful — returns AuthResponse containing the JWT token</response>
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

        /// <summary>Request a 6-digit OTP for password reset</summary>
        /// <remarks>
        /// Generates a secure 6-digit one-time password and sends it to the user's email.
        /// Always returns the same successful response to prevent account enumeration.
        /// The OTP expires after <b>15 minutes</b>.
        /// </remarks>
        [HttpPost("forgot-password")]
        [ProducesResponseType<string>(200)]
        public async Task<IActionResult> ForgotPasswordAsync(
            [FromBody] ForgotPasswordRequestDto request)
        {
            var result = await authService.ForgotPasswordAsync(request);
            return Ok(result.Message);
        }

        /// <summary>Reset a password using the 6-digit OTP</summary>
        /// <remarks>
        /// Validates the OTP sent to the user's email, then updates the password.
        /// Returns <b>400</b> if the OTP is incorrect or has expired.
        /// </remarks>
        [HttpPost("reset-password")]
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(400)]
        public async Task<IActionResult> ResetPasswordAsync(
            [FromBody] ResetPasswordRequestDto request)
        {
            var result = await authService.ResetPasswordAsync(request);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }

        /// <summary>Change the current user's password</summary>
        /// <remarks>
        /// Requires the user to be authenticated and to provide their current password.
        /// </remarks>
        [HttpPost("change-password")]
        [Authorize]
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        public async Task<IActionResult> ChangePasswordAsync(
            [FromBody] ChangePasswordRequestDto request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await authService.ChangePasswordAsync(userId, request);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }
    }
}
