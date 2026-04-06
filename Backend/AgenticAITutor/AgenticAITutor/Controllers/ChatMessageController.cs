using AgenticAITutor.Extensions;
using AgenticAITutor.Models;
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

        /// <summary>Send a message and receive an AI response</summary>
        /// <remarks>
        /// Set **searchWeb: true** to query the web, or **false** to query your uploaded documents.
        /// Provide **allowedDocumentIds** to restrict which documents the AI can reference.
        /// </remarks>
        /// <response code="200">AI response with optional document citations</response>
        /// <response code="400">Message processing failed</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<AIMessageResponse>(200)]
        [ProducesResponseType<WebSearchResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpPost("SendMessage")]
        public async Task<IActionResult> SendMessage([FromBody] UserMessageRequest request)
        {
            var userId = User.GetUserId();
            if(userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            if(!ModelState.IsValid)
                return BadRequest(ModelState);

            request.UserId = userId;


            if (request.SearchWeb)
            {
                var webResponse = await messageService.SendWebMessageAsync(request);

                if (!webResponse.Success)
                    return BadRequest(webResponse.Message);

                return Ok(webResponse.Data);
            }
            else
            {
                var aiResponse = await messageService.SendAIMessageAsync(request);
                if (!aiResponse.Success)
                    return BadRequest(aiResponse.Message);

                return Ok(aiResponse.Data);
            }
        }

        /// <summary>Get all messages in a chat session</summary>
        /// <param name="sessionId">Session GUID</param>
        /// <response code="200">List of messages</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation Error</response>
        [ProducesResponseType<List<ChatMessage>>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
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
