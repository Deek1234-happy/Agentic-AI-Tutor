using AgenticAITutor.Extensions;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class ChatSessionController : ControllerBase
    {
        private readonly IChatSessionService sessionService;

        public ChatSessionController(IChatSessionService sessionService)
        {
            this.sessionService = sessionService;
        }

        /// <summary>Create a new chat session</summary>
        /// <remarks>
        /// Initializes a new chat session. Pass a list of `DocumentIds` to scope the AI context.
        /// The JWT Token must be passed in the `Authorization` header.
        /// </remarks>
        /// <param name="request">Contains an optional list of `DocumentIds`.</param>
        /// <response code="200">Session created — returns ChatSessionResponse</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error or Document ID does not belong to user</response>
        [ProducesResponseType<ChatSessionResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpPost]
        public async Task<IActionResult> CreateSession([FromBody] ChatSessionRequest request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            request.UserId = userId;
            
            var result = await sessionService.CreateSessionAsync(request);
            if(!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Data);
        }

        /// <summary>Get all chat sessions for the current user(Chat History)</summary>
        /// <response code="200">List of chat sessions</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error</response>
        [ProducesResponseType<List<ChatSessionResponse>>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpGet]
        public async Task<IActionResult> GetUserSessions()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await sessionService.GetUserSessionsAsync(userId);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Data);
        }
        /// <summary>Update the title of a chat session</summary>
        /// <remarks>
        /// Allows the user or frontend to dynamically rename a chat session.
        /// </remarks>
        /// <param name="request">Contains the `SessionId` and the new `Title`.</param>
        /// <response code="200">Title updated successfully</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error or Session Not Found</response>
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpPut]
        public async Task<IActionResult> UpdateSessionTitleAsync([FromBody] ChatSessionUpdate request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            request.UserId=userId;

            var result = await sessionService.UpdateSessionAsync(request);
            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }

        /// <summary>Delete a chat session by ID</summary>
        /// <param name="sessionId">Session GUID</param>
        /// <response code="200">Session deleted</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error</response>
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpDelete("{sessionId}")]
        public async Task<IActionResult> DeleteSessionAsync(Guid sessionId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await sessionService.DeleteSessionAsync(userId,sessionId);
            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }
    }
}
