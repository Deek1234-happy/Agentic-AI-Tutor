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

        [HttpPost]
        public async Task<IActionResult> Add([FromBody]SubjectModel subjectModel)
        {
            if(!ModelState.IsValid) 
                return BadRequest(ModelState);

            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            subjectModel.UserId = userId;
            string result = await subjectService.AddAsync(subjectModel);
            return Ok(result);
        }
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            var subjects = await subjectService.GetAllAsync(userId);
            return Ok(subjects);

        }

        [HttpGet("{name}")]
        public async Task<IActionResult> Get(string name)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            SubjectModel subjectModel = new SubjectModel
            {
                UserId = userId,
                Name = name.ToLower()
            };
            Subject subject = await subjectService.GetAsync(subjectModel);
            
            if (subject == null)
                return NotFound($"Subject {name} is not found");
            return Ok(subject);
        }

        [HttpPut]
        public async Task<IActionResult> Update([FromBody] UpdateSubjectRequest updateSubjectRequest)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            
            var result = await subjectService.UpdateAsync(updateSubjectRequest.OldName.ToLower(), updateSubjectRequest.NewName.ToLower(), userId);

            if (result.Contains("no Subject"))
                return NotFound(result);

            if (result.Contains("already have"))
                return BadRequest(result);

            return Ok(result);
        }

        [HttpDelete("{name}")]
        public async Task<IActionResult> Delete(string name)
        {
            var userId = User.GetUserId();

            var model = new SubjectModel
            {
                Name = name.ToLower(),
                UserId = userId
            };

            var result = await subjectService.DeleteAsync(model);

            if (result.Contains("no Subject"))
                return NotFound(result);

            return Ok(result);
        }
    }
}
    