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
        /// Forget About UserId and Allowed Document Ids Don't Send Them in The Request
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
        /// Forget About UserId and Allowed Document Ids Don't Send Them in The Request
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

        ///// <summary>Send a voice message and receive an AI voice response</summary>
        ///// <response code="200">AI audio response with transcript and citations</response>
        ///// <response code="400">Audio processing failed</response>
        ///// <response code="401">Invalid or missing token</response>
        //[HttpPost("SendVoiceMessage")]
        //[Consumes("multipart/form-data")] // Tells Swagger and the Mobile App to expect a file
        //[ProducesResponseType<AIAudioResponse>(200)]
        //[ProducesResponseType<string>(400)]
        //[ProducesResponseType<string>(401)]
        //public async Task<IActionResult> SendVoiceMessage([FromForm] UserAudioRequest request)
        //{
        //    var userId = User.GetUserId();
        //    if (userId == Guid.Empty)
        //        return Unauthorized("Invalid Token.");

        //    // Ensure the user actually uploaded a file
        //    if (request.Audio == null || request.Audio.Length == 0)
        //        return BadRequest("No audio file was provided.");

        //    // Security: Override the DTO UserId with the trusted Token ID
        //    request.UserId = userId;

        //    var response = await messageService.SendVoiceMessageAsync(request);

        //    if (!response.Success)
        //        return BadRequest(response.Message);

        //    return Ok(response.Data);
        //}

        /// <summary>Get all messages in a chat session</summary>
        /// <param name="sessionId">Session GUID</param>
        /// <response code="200">List of messages</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation Error</response>
        [ProducesResponseType<List<ChatMessageResponse>>(200)]
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

        /// <summary>Convert an audio file to text (Transcribtion)</summary>
        /// <response code="200">Returns the transcribed text</response>
        /// <response code="400">Audio processing failed or missing file</response>
        /// <response code="401">Invalid or missing token</response>
        [HttpPost("STT")]
        [Consumes("multipart/form-data")]
        [ProducesResponseType<STTResponse>(200)] // Tells Swagger EXACTLY what the JSON looks like!
        [ProducesResponseType<string>(400)]
        public async Task<IActionResult> SpeechToText(IFormFile audio_file)
        {
            // Security: Ensure the user is authenticated before allowing AI usage
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await messageService.SpeechToTextAsync(audio_file);

            if (!result.Success)
                return BadRequest(result.Message);

            // Use the strict DTO instead of an anonymous object
            var response = new STTResponse { Text = result.Data };

            return Ok(response);
        }

        /// <summary>Generate playable audio for an existing AI message</summary>
        /// <param name="messageId">The GUID of the AI's chat message</param>
        /// <response code="200">Returns the URL of the generated audio file</response>
        /// <response code="400">TTS generation failed or unauthorized access</response>
        /// <response code="401">Invalid or missing token</response>
        [HttpPost("{messageId}/TTS")]
        [ProducesResponseType<TTSResponse>(200)] // Perfect Swagger Docs!
        [ProducesResponseType<string>(400)]
        public async Task<IActionResult> TextToSpeech(Guid messageId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await messageService.TextToSpeechAsync(messageId, userId);

            if (!result.Success)
                return BadRequest(result.Message);

            var response = new TTSResponse { AudioUrl = result.Data };

            return Ok(response);
        }
    }
}
