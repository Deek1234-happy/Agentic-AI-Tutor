using AgenticAITutor.Extensions;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class DocumentChunkController : ControllerBase
    {
        private readonly IDocumentChunkService chunkService;

        public DocumentChunkController(IDocumentChunkService chunkService)
        {
            this.chunkService = chunkService;
        }

        /// <summary>Get chunks for a specific document</summary>
        /// <remarks>
        /// Retrieves the processed chunks (text segments) of an uploaded document.
        /// This is useful for frontend debugging or displaying how the document was split for RAG.
        /// </remarks>
        /// <param name="documentId">The GUID of the document</param>
        /// <response code="200">Returns a list of document chunks</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="404">No chunks found or document is still processing</response>
        [ProducesResponseType(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        [HttpGet("{documentId}")]
        public async Task <IActionResult> GetChunks(Guid documentId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var chunks = await chunkService.GetDocumentChunksAsync(documentId, userId);
            if (chunks == null || chunks.Count == 0)
            {
                return NotFound("No chunks found for this document. It may not exist or is still processing.");
            }

            return Ok(chunks);
        }

    }
}
