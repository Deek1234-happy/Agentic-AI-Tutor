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

        [HttpDelete("{sessionId}")]
        public async Task<IActionResult> DeleteSessionAsync([FromHeader] Guid sessionId)
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
