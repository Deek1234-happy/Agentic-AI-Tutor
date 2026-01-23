using AgenticAITutor.Models.DTOs.Auth;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly IAuthService authService;

        public AuthController(IAuthService authService)
        {
            this.authService = authService;
        }

        [HttpPost("register")]
        public async Task<IActionResult> RegisterAsync([FromBody]RegisterRequest request)
        {
            if(!ModelState.IsValid)
                return BadRequest(ModelState);

            var result = await authService.RegisterAsync(request);

            if(!result.IsAuthenticated)
                return BadRequest(result.Message);

            return Ok(result);
        }
    }
}
