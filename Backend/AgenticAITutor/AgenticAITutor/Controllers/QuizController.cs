using AgenticAITutor.Extensions;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.Enums;
using AgenticAITutor.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class QuizController : ControllerBase
    {
        private readonly IQuizService _quizService;

        public QuizController(IQuizService quizService)
        {
            _quizService = quizService;
        }

        /// <summary>Initiate quiz generation or reuse a cached quiz</summary>
        /// <remarks>
        /// Computes a hash from userId + sorted documentIds.
        /// - Returns **200** if an identical READY quiz already exists (cache hit).
        /// - Returns **202** if a new generation job was enqueued.
        /// - Returns **409** if generation is already in progress for this combination.
        /// - Returns **400** on validation errors (invalid documents, subject, etc.).
        /// </remarks>
        [HttpPost("initiate")]
        [ProducesResponseType<QuizInitiateResponse>(200)]
        [ProducesResponseType<QuizInitiateResponse>(202)]
        [ProducesResponseType<QuizInitiateResponse>(409)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        public async Task<IActionResult> Initiate([FromBody] QuizInitiateRequest request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.InitiateAsync(userId, request);

            if (result.Data == null)
                return BadRequest(result.Message);

            return result.Data.Status switch
            {
                var s when s == QuizStatus.READY.ToString()
                    => Ok(result.Data),
                var s when s == QuizStatus.GENERATING.ToString() && result.Success
                    => StatusCode(202, result.Data),
                var s when s == QuizStatus.GENERATING.ToString() && !result.Success
                    => Conflict(result.Data),
                _ => BadRequest(result.Message)
            };
        }

        /// <summary>Poll quiz generation status</summary>
        /// <remarks>Returns GENERATING, READY, or FAILED.</remarks>
        /// <param name="quizId">Quiz GUID</param>
        [HttpGet("{quizId}/status")]
        [ProducesResponseType<QuizStatusResponse>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        public async Task<IActionResult> GetStatus(Guid quizId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.GetStatusAsync(userId, quizId);
            if (!result.Success) return NotFound(result.Message);
            return Ok(result.Data);
        }

        /// <summary>Start a quiz exam attempt</summary>
        /// <remarks>
        /// Creates a new attempt row. Options are shuffled server-side using Fisher-Yates
        /// seeded by the attemptId. The shuffle mapping is stored server-side only —
        /// the response contains **no correct-answer information**.
        /// </remarks>
        /// <param name="quizId">Quiz GUID</param>
        [HttpGet("{quizId}/start")]
        [ProducesResponseType<QuizStartResponse>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        public async Task<IActionResult> Start(Guid quizId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.StartAsync(userId, quizId);
            if (!result.Success) return BadRequest(result.Message);
            return Ok(result.Data);
        }

        /// <summary>Submit answers and receive a score</summary>
        /// <remarks>
        /// **Idempotent** — submitting the same attemptId twice returns the original score.
        /// The server reverse-maps shuffled option labels to original labels before scoring.
        /// </remarks>
        /// <param name="quizId">Quiz GUID</param>
        [HttpPost("{quizId}/submit")]
        [ProducesResponseType<QuizSubmitResponse>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        public async Task<IActionResult> Submit(Guid quizId, [FromBody] QuizSubmitRequest request)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.SubmitAsync(userId, quizId, request);
            if (!result.Success) return BadRequest(result.Message);
            return Ok(result.Data);
        }

        /// <summary>List all attempts for a quiz by the current user</summary>
        /// <param name="quizId">Quiz GUID</param>
        [HttpGet("{quizId}/attempts")]
        [ProducesResponseType<List<QuizAttemptSummary>>(200)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        public async Task<IActionResult> GetAttempts(Guid quizId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.GetAttemptsAsync(userId, quizId);
            if (!result.Success) return NotFound(result.Message);
            return Ok(result.Data);
        }

        /// <summary>Full review of a completed attempt</summary>
        /// <remarks>
        /// Returns correct answers, the student's answers, AI explanations, and
        /// source chunk citations for each question.
        /// </remarks>
        /// <param name="attemptId">Attempt GUID</param>
        [HttpGet("attempt/{attemptId}/review")]
        [ProducesResponseType<QuizReviewResponse>(200)]
        [ProducesResponseType<string>(400)]
        [ProducesResponseType<string>(401)]
        [ProducesResponseType<string>(404)]
        public async Task<IActionResult> GetReview(Guid attemptId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.GetReviewAsync(userId, attemptId);
            if (!result.Success) return BadRequest(result.Message);
            return Ok(result.Data);
        }

        /// <summary>Paginated, filterable history of all quizzes generated by the user</summary>
        [HttpGet("history")]
        [ProducesResponseType<List<QuizHistoryItem>>(200)]
        [ProducesResponseType<string>(401)]
        public async Task<IActionResult> GetHistory([FromQuery] QuizHistoryFilter filter)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.GetHistoryAsync(userId, filter);
            return Ok(result.Data);
        }

        /// <summary>All quizzes for a specific subject</summary>
        /// <param name="subjectId">Subject GUID</param>
        [HttpGet("subject/{subjectId}")]
        [ProducesResponseType<List<QuizHistoryItem>>(200)]
        [ProducesResponseType<string>(401)]
        public async Task<IActionResult> GetBySubject(Guid subjectId)
        {
            var userId = User.GetUserId();
            if (userId == Guid.Empty) return Unauthorized("Invalid Token.");

            var result = await _quizService.GetBySubjectAsync(userId, subjectId);
            return Ok(result.Data);
        }
    }
}
