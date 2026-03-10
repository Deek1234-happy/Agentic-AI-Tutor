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
    public class ChatMessageController : ControllerBase
    {
        private readonly IChatMessageService messageService;

        public ChatMessageController(IChatMessageService messageService)
        {
            this.messageService = messageService;
        }

        [HttpPost]
        public async Task<IActionResult> SendMessage([FromBody] UserMessageRequest request)
        {
            var userId = User.GetUserId();
            if(userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            request.UserId = userId;

            var response = await messageService.SendMessageAsync(request);
            if(!response.Success)
                return BadRequest(response.Message);

            return Ok(response.Data);
        }

        [HttpGet("{sessionId}")]
        public async Task<IActionResult> GetSessionMessages(Guid sessionId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var response = await messageService.GetSessionMessagesAsync(userId, sessionId);
            if (!response.Success)
                return BadRequest(response.Message);

            return Ok(response.Data);
        }
    }
}
