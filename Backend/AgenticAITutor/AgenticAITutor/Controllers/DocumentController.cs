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

        /// <summary>Upload a new document</summary>
        /// <remarks>Accepts multipart/form-data. The file is processed and chunked after upload.</remarks>
        /// <response code="200">Document uploaded and processed</response>
        /// <response code="400">Validation error</response>
        /// <response code="401">Invalid or missing token</response>
        [HttpPost]
        [ProducesResponseType<DocumentResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
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
                return BadRequest(result.Message);
            return Ok(result);
        }

        /// <summary>Update document metadata (title or subject)</summary>
        /// <response code="200">Document updated</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error</response>
        [ProducesResponseType<DocumentResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
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
                return BadRequest(result.Message);
            return Ok(result);
        }

        /// <summary>Delete a document by ID</summary>
        /// <param name="id">Document GUID</param>
        /// <response code="200">Document deleted</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error</response>
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
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

        /// <summary>Get all documents for the current user</summary>
        /// <response code="200">List of documents</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<List<DocumentResponse>>(200)]
        [ProducesResponseType<string>(401)]
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var documents = await documentService.GetAllDocumentsAsync(userId);
            
            return Ok(documents);
        }

        /// <summary>Get all documents under a specific subject</summary>
        /// <param name="subjectId">Subject GUID</param>
        /// <response code="200">List of documents</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<List<DocumentResponse>>(200)]
        [ProducesResponseType<string>(401)]
        [HttpGet("subject/{subjectId}")]
        public async Task<IActionResult> GetBySubject(Guid subjectId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var documents = await documentService.GetDocumentsBySubjectAsync(userId, subjectId);

            return Ok(documents);
        }


        /// <summary>Get a document by ID</summary>
        /// <param name="id">Document GUID</param>
        /// <response code="200">Document details</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<DocumentResponse>(200)]
        [ProducesResponseType<string>(401)]
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var document = await documentService.GetDocumentsByIdAsync(userId, id);

            return Ok(document);
        }

    }
}
