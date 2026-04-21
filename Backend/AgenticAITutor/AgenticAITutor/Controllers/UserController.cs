using AgenticAITutor.Extensions;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.ModelBinding;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class UserController : ControllerBase
    {
        private readonly IUserService userService;

        public UserController(IUserService userService)
        {
            this.userService = userService;
        }

        /// <summary>Get the current user's profile</summary>
        /// <remarks>
        /// Fetches the profile data (FirstName, LastName, Email) for the currently authenticated user.
        /// </remarks>
        /// <response code="200">Returns UserResponse profile data</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="404">User not found</response>
        [HttpGet("profile")]
        [ProducesResponseType<UserResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        public async Task<IActionResult> GetProfile()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var user = await userService.GetByIdAsync(userId);
            if (!user.Success)
                return NotFound(user.Message);

            return Ok(user.Data);
        }

        /// <summary>Update the current user's profile</summary>
        /// <remarks>
        /// Updates the authenticated user's Data
        /// </remarks>
        /// <param name="request">Contains the new `FirstName` `LastName` and/or `Email`.</param>
        /// <response code="200">Profile updated successfully — returns UserResponse</response>
        /// <response code="400">Validation error</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<UserResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        [HttpPut("profile")]
        public async Task<IActionResult> UpdateProfile([FromBody] UserUpdateRequest request)
        {
            if (!ModelState.IsValid)
                return BadRequest(ModelState);

            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await userService.UpdateAsync(userId, request);

            if(!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Data);
        }

        /// <summary>Delete the current user's account permanently</summary>
        /// <response code="200">Account deleted Successfully</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error</response>
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        [HttpDelete("profile")]
        public async Task<IActionResult> DeleteProfile()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await userService.DeleteAsync(userId);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }
    }
}
