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
            List<SubjectModel> subjectModels = new List<SubjectModel>();
            foreach(var subject in subjects)
            {
                SubjectModel subjectModel = new SubjectModel
                {
                    Id = subject.Id,
                    UserId = subject.UserId,
                    Name = subject.Name,
                };
                subjectModels.Add(subjectModel);
            }
            return Ok(subjectModels);

        }

        [HttpGet("{id}")]
        public async Task<IActionResult> Get(Guid id)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty)
                return Unauthorized("Invalid Token : User ID Not Found");

            Subject subject = await subjectService.GetAsync(id, userId);
            
            if (subject == null)
                return NotFound("Subject is not found");

            SubjectModel subjectModel = new SubjectModel
            {
                Id = id,
                Name = subject.Name,
                UserId = userId
            };
            return Ok(subjectModel);
        }

        [HttpPut("{id}")]
        public async Task<IActionResult> Update(Guid id, [FromBody] SubjectModel subjectModel)
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

        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(Guid id)
        {
            var userId = User.GetUserId();

            var result = await subjectService.DeleteAsync(id, userId);

            if (!result.Success)
                return BadRequest(result.Message);

            return Ok(result.Message);
        }
    }
}
    