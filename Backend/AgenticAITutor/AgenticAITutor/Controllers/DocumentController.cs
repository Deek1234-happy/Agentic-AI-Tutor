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
        private readonly IWebHostEnvironment webHostEnvironment;

        public DocumentController(IDocumentService documentService, IWebHostEnvironment webHostEnvironment)
        {
            this.documentService = documentService;
            this.webHostEnvironment = webHostEnvironment;
        }

        /// <summary>Upload a new document</summary>
        /// <remarks>
        /// Accepts a file upload via `multipart/form-data`. 
        /// **Required Fields:** `File` (the physical file), `SubjectId` (groups the document).
        /// After upload, the file is queued for background processing (text extraction and chunking).
        /// </remarks>
        /// <param name="request">Multipart form data containing the file</param>
        /// <response code="200">Document uploaded and queued for processing — returns DocumentResponse</response>
        /// <response code="400">Validation error (e.g., file too large or invalid format)</response>
        /// <response code="401">Invalid or missing token</response>
        [HttpPost]
        [ProducesResponseType<DocumentResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [RequestSizeLimit(10 * 1024 * 1024)]
        [RequestFormLimits(MultipartBodyLengthLimit = 10 * 1024 * 1024)]
        public async Task<IActionResult> Upload([FromForm]DocumentRequest request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            request.UserId = userId;
            
            var result = await documentService.UploadDocumentAsync(request);
            if(!result.Success)
                return BadRequest(result.Message);
            return Ok(result.Data);
        }

        /// <summary>Update document metadata (title or subject)</summary>
        /// <remarks>
        /// Allows changing a document's Title, associating it with a new Subject.
        /// </remarks>
        /// <param name="request">Contains the new metadata</param>
        /// <response code="200">Document updated successfully — returns updated DocumentResponse</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation error or Document not found</response>
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
            return Ok(result.Data);
        }

        /// <summary>Delete a document by ID</summary>
        /// <remarks>
        /// Permanently deletes a document.
        /// **Warning:** This deletes the database record, the physical file in storage, and triggers a purge of all associated AI Knowledge Graph entities.
        /// </remarks>
        /// <param name="id">Document GUID</param>
        /// <response code="200">Document deleted successfully</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Document not found or belongs to another user</response>
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
                return BadRequest(result.Message);
            return Ok(result.Message);
        }

        /// <summary>Get all documents for the current user</summary>
        /// <remarks>
        /// Retrieves every document uploaded by the authenticated user, regardless of subject.
        /// </remarks>
        /// <response code="200">List of DocumentResponse objects</response>
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

        /// <summary>Retry processing a document that previously failed</summary>
        /// <param name="id">Document GUID</param>
        /// <remarks>
        /// Only documents with a **FAILED** processing status can be retried.
        /// Attempting to retry a PENDING, PROCESSING, or COMPLETED document will return 400.
        /// On success the document status is reset to PENDING and the chunking job is re-queued.
        /// </remarks>
        /// <response code="200">Document re-queued — returns updated document</response>
        /// <response code="400">Document is not in FAILED status, or validation error</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<DocumentResponse>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [HttpPost("{id}/retry-processing")]
        public async Task<IActionResult> RetryProcessing(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            var result = await documentService.RetryDocumentProcessingAsync(id, userId);
            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Data);
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

        /// <summary>Securely view or download a document</summary>
        /// <param name="id">Document GUID</param>
        /// <response code="200">File stream returned</response>
        /// <response code="404">Document or physical file not found</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType(typeof(FileResult), 200)]
        [ProducesResponseType<string>(404)]
        [ProducesResponseType<string>(401)]
        [HttpGet("{id}/download")]
        public async Task<IActionResult> Download(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token.");

            // GetDocumentsByIdAsync internally ensures that the document belongs to the requesting user
            var document = await documentService.GetDocumentsByIdAsync(userId, id);
            if (document == null)
                return NotFound("Document not found.");

            string webRootPath = webHostEnvironment.WebRootPath;
            if (string.IsNullOrEmpty(webRootPath))
                webRootPath = Path.Combine(webHostEnvironment.ContentRootPath, "wwwroot");

            // Prevent path traversal
            var safeRelativePath = document.StoragePath.TrimStart('/', '\\');
            var filePath = Path.GetFullPath(Path.Combine(webRootPath, safeRelativePath));

            if (!filePath.StartsWith(Path.GetFullPath(webRootPath)))
            {
                return BadRequest("Invalid file path.");
            }

            if (!System.IO.File.Exists(filePath))
                return NotFound("Physical file not found on server.");

            var provider = new Microsoft.AspNetCore.StaticFiles.FileExtensionContentTypeProvider();
            if (!provider.TryGetContentType(filePath, out var contentType))
            {
                contentType = "application/octet-stream";
            }

            // By not providing a third argument (fileDownloadName), 
            // browsers will try to display it inline (like PDFs) instead of forcing a download.
            return PhysicalFile(filePath, contentType);
        }

    }
}
