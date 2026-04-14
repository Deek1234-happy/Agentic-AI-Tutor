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
