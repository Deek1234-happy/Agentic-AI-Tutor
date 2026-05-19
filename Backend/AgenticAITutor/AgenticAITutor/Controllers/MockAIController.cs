using AgenticAITutor.Models.DTOs;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    /// <summary>
    /// Mock AI controller — simulates the Python AI service during development.
    /// Remove or disable in production by switching AIService:BaseURL back to the real Python service.
    /// </summary>
    [Route("api/mock-ai")]
    [ApiController]
    public class MockAIController : ControllerBase
    {
        private static readonly Random _rng = new(42);

        // ── Bloom levels and distractor patterns ────────────────────────────────
        private static readonly string[] BloomLevels =
            { "remember", "understand", "apply", "analyze", "evaluate", "create" };

        private static readonly string[] DistractorSuffixes =
            { " (incorrect)", " (not applicable)", " (partially true)", " (out of scope)" };

        // ────────────────────────────────────────────────────────────────────────

        /// <summary>Mock MCQ generation endpoint — mirrors POST /quiz/generate on the Python service</summary>
        /// <remarks>
        /// Accepts the same <c>McqGenerateRequest</c> the real AI service expects and returns
        /// a realistic <c>McqGenerateResponse</c> with one generated question per chunk.
        /// Each question has 4 options (A–D), a randomised correct answer, an explanation,
        /// bloom level, concept, and citation chunk IDs.
        /// </remarks>
        [HttpPost("quiz/generate")]
        [ProducesResponseType<McqGenerateResponse>(200)]
        public IActionResult GenerateQuiz([FromBody] McqGenerateRequest request)
        {
            if (request?.Chunks == null || !request.Chunks.Any())
                return BadRequest("No chunks provided.");

            var questions = new List<McqGeneratedQuestion>();

            foreach (var chunk in request.Chunks)
            {
                // Derive a short concept label from concepts list or fall back to chunk text
                var concept = chunk.Concepts?.FirstOrDefault()
                    ?? TruncateWords(chunk.Text, 4);

                var bloomLevel = !string.IsNullOrWhiteSpace(chunk.BloomLevel)
                    ? chunk.BloomLevel
                    : BloomLevels[_rng.Next(BloomLevels.Length)];

                // Build 4 plausible-sounding options from the chunk text
                var correctText = $"The correct statement about '{concept}': {TruncateWords(chunk.Text, 10)}.";
                var optionTexts = new[]
                {
                    correctText,
                    $"'{concept}' is primarily used for {GetDistractor(chunk.Text, 0)}.",
                    $"'{concept}' always requires {GetDistractor(chunk.Text, 1)}.",
                    $"'{concept}' has no relation to {GetDistractor(chunk.Text, 2)}."
                };

                // Fisher-Yates shuffle so correct answer is not always A
                var indices = new[] { 0, 1, 2, 3 };
                for (int i = 3; i > 0; i--)
                {
                    int j = _rng.Next(i + 1);
                    (indices[i], indices[j]) = (indices[j], indices[i]);
                }

                char[] labels = { 'A', 'B', 'C', 'D' };
                char correctLabel = 'A';
                var options = new List<McqGeneratedOption>();
                for (int i = 0; i < 4; i++)
                {
                    options.Add(new McqGeneratedOption
                    {
                        Label = labels[i],
                        Text = optionTexts[indices[i]]
                    });
                    if (indices[i] == 0) // index 0 is always the correct option text
                        correctLabel = labels[i];
                }

                questions.Add(new McqGeneratedQuestion
                {
                    QuestionText = $"Which of the following best describes '{concept}' based on the course material?",
                    CorrectOption = correctLabel,
                    Explanation = $"According to the source material: \"{TruncateWords(chunk.Text, 20)}\". " +
                                  $"This aligns with the {bloomLevel} level of Bloom's taxonomy for the concept '{concept}'.",
                    Concept = concept,
                    BloomLevel = bloomLevel,
                    ChunkId = chunk.ChunkId,
                    CitationChunkIds = new List<Guid> { chunk.ChunkId },
                    Options = options
                });
            }

            return Ok(new McqGenerateResponse { Questions = questions });
        }

        // ── Private helpers ────────────────────────────────────────────────────

        private static string TruncateWords(string text, int wordCount)
        {
            if (string.IsNullOrWhiteSpace(text)) return "this topic";
            var words = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            return string.Join(' ', words.Take(wordCount)).TrimEnd('.', ',', ';');
        }

        private static string GetDistractor(string text, int seed)
        {
            // Picks a few words from middle of chunk text to create a plausible distractor
            var words = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (words.Length < 4) return "external dependencies" + DistractorSuffixes[seed % DistractorSuffixes.Length];
            int start = Math.Min(seed * 3 + 2, words.Length - 3);
            return string.Join(' ', words.Skip(start).Take(3)) + DistractorSuffixes[seed % DistractorSuffixes.Length];
        }
    }
}
