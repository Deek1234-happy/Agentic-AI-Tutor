using AgenticAITutor.Extensions;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.DTOs.ChatMessage;
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
        /// Set **searchWeb: False** to query your uploaded documents.
        /// </remarks>
        /// <response code="200">AI response with document citations</response>
        /// <response code="400">Message processing failed or Validation Error</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<AIMessageResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpPost("SendMessage")]
        public async Task<IActionResult> SendAIMessage([FromBody] UserMessageRequest request)
        {
            var userId = User.GetUserId();
            if(userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            if(!ModelState.IsValid)
                return BadRequest(ModelState);

            if (request.SearchWeb)
                return BadRequest("Search Web Must Be False");
            
            
            request.UserId = userId;
            var aiResponse = await messageService.SendAIMessageAsync(request);
            if (!aiResponse.Success)
                return BadRequest(aiResponse.Message);

            return Ok(aiResponse.Data);
            
        }

        /// <summary>Send a message and receive a Web Search response</summary>
        /// <remarks>
        /// Set **searchWeb: true** to query the web
        /// </remarks>
        /// <response code="200">Web Search response with Sources</response>
        /// <response code="400">Message processing failed or Validation Error</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<WebSearchResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpPost("SearchWeb")]
        public async Task<IActionResult> SearchWeb([FromBody]UserMessageRequest request)
        {
            var userId = User.GetUserId();
            if(userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            if(!ModelState.IsValid)
                return BadRequest(ModelState);

            if (!request.SearchWeb)
                return BadRequest("Search Web Must Be True");

            request.UserId = userId;
            var webResponse = await messageService.SendWebMessageAsync(request);

            if (!webResponse.Success)
                return BadRequest(webResponse.Message);

            return Ok(webResponse.Data);
        }

        /// <summary>Send a voice message and receive an AI voice response</summary>
        /// <response code="200">AI audio response with transcript and citations</response>
        /// <response code="400">Audio processing failed</response>
        /// <response code="401">Invalid or missing token</response>
        [HttpPost("SendVoiceMessage")]
        [Consumes("multipart/form-data")] // Tells Swagger and the Mobile App to expect a file
        [ProducesResponseType<AIAudioResponse>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        public async Task<IActionResult> SendVoiceMessage([FromForm] UserAudioRequest request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            // Ensure the user actually uploaded a file
            if (request.Audio == null || request.Audio.Length == 0)
                return BadRequest("No audio file was provided.");

            // Security: Override the DTO UserId with the trusted Token ID
            request.UserId = userId;

            var response = await messageService.SendVoiceMessageAsync(request);

            if (!response.Success)
                return BadRequest(response.Message);

            return Ok(response.Data);
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
