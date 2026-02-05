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
    public class DocumentController : ControllerBase
    {
        private readonly IDocumentService documentService;

        public DocumentController(IDocumentService documentService)
        {
            this.documentService = documentService;
        }

        [HttpPost]
        public async Task<IActionResult> Upload([FromForm]DocumentRequest request)
        {
            if(!ModelState.IsValid)
                return BadRequest(ModelState);
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            request.UserId = userId;
            
            var result = await documentService.UploadDocumentAsync(request);
            if(!result.Success)
                return BadRequest(result);
            return Ok(result);
        }

        [HttpPut]
        public async Task<IActionResult> Update([FromBody]DocumentUpdate request)
        {
            if (!ModelState.IsValid)
                return BadRequest(ModelState);
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            request.UserId = userId;

            var result = await documentService.UpdateDocumentAsync(request);
            if (!result.Success)
                return BadRequest(result);
            return Ok(result);
        }

        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await documentService.DeleteDocumentAsync(id, userId);
            if (!result.Success)
                return BadRequest(result);
            return Ok(result);
        }

        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var documents = await documentService.GetAllDocumentsAsync(userId);
            
            return Ok(documents);
        }

        [HttpGet("subject/{subjectId}")]
        public async Task<IActionResult> GetBySubject(Guid subjectId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var documents = await documentService.GetDocumentsBySubjectAsync(userId, subjectId);

            return Ok(documents);
        }
    }
}
