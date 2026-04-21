using AgenticAITutor.Extensions;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class SubjectController : ControllerBase
    {
        private readonly ISubjectService subjectService;

        public SubjectController(ISubjectService subjectService)
        {
            this.subjectService = subjectService;
        }

        /// <summary>Create a new study subject</summary>
        /// <remarks>
        /// Subjects act as folders to group related documents together.
        /// Subject names must be unique per user.
        /// </remarks>
        /// <param name="subjectRequest">Contains the `Name` of the new subject.</param>
        /// <response code="200">Subject created successfully — returns SubjectResponse</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation Error or Subject Name already exists</response>
        [ProducesResponseType<SubjectResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(400)]
        [HttpPost]
        public async Task<IActionResult> Add([FromBody]SubjectRequest subjectRequest)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            subjectRequest.UserId = userId;
            var result = await subjectService.AddAsync(subjectRequest);
            if(!result.Success)
                return BadRequest(result.Message);

            SubjectResponse subjectResponse = result?.Data;
            
            return Ok(subjectResponse);
        }

        /// <summary>Get all subjects for the current user</summary>
        /// <remarks>
        /// Retrieves a list of all subjects created by the authenticated user, along with a nested list of their associated Documents.
        /// </remarks>
        /// <response code="200">List of subjects and their documents</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<List<SubjectResponse>>(200)]
        [ProducesResponseType<string>(401)]
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            var subjectResponses = await subjectService.GetAllAsync(userId);

            return Ok(subjectResponses);

        }

        /// <summary>Get a subject by ID</summary>
        /// <param name="id">Subject GUID</param>
        /// <response code="200">Subject found</response>
        /// <response code="404">Subject not found</response>
        /// <response code="401">Invalid or missing token</response>
        [ProducesResponseType<SubjectResponse>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        [HttpGet("{id}")]
        public async Task<IActionResult> Get(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            var result = await subjectService.GetAsync(id, userId);
            
            if (!result.Success)
                return NotFound(result.Message);

            SubjectResponse subjectResponse = result?.Data;
            return Ok(subjectResponse);
        }

        /// <summary>Update a subject by ID</summary>
        /// <remarks>
        /// Updates the name of an existing subject.
        /// </remarks>
        /// <param name="id">Subject GUID</param>
        /// <param name="subjectModel">Contains the new `Name` for the subject.</param>
        /// <response code="200">Subject updated successfully</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Validation Error or Name already exists</response>
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [HttpPut("{id}")]
        public async Task<IActionResult> Update(Guid id, [FromBody] SubjectRequest subjectModel)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            subjectModel.UserId = userId;
            var result = await subjectService.UpdateAsync(id, subjectModel);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }

        /// <summary>Delete a subject by ID</summary>
        /// <remarks>
        /// Deletes the subject. 
        /// **Warning:** This will also permanently delete all Documents grouped under this subject, including their physical files and AI Knowledge Graph data.
        /// </remarks>
        /// <param name="id">Subject GUID</param>
        /// <response code="200">Subject and its associated documents deleted</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="400">Subject not found or validation error</response>
        [ProducesResponseType<string>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            var result = await subjectService.DeleteAsync(id, userId);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }

        /// <summary>Get documents for a subject (Dropdown Optimized)</summary>
        /// <remarks>
        /// Returns a lightweight list containing only the `Id` and `FileName` of the documents belonging to a subject.
        /// Optimized for use in dropdown menus when creating a new Chat Session.
        /// </remarks>
        /// <param name="id">Subject GUID</param>
        /// <response code="200">List of document dropdown items</response>
        /// <response code="401">Invalid or missing token</response>
        /// <response code="404">Subject not found</response>
        [ProducesResponseType<List<DocumentDropdownResponse>>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        [HttpGet("{id}/documents/dropdown")]
        public async Task<IActionResult> GetSubjectDocumentsDropdown(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            var result = await subjectService.GetDocumentsForDropdownAsync(id, userId);

            if (!result.Success)
                return NotFound(result.Message);

            return Ok(result.Data);
        }
    }
}
    