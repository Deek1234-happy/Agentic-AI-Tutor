using AgenticAITutor.Models.DTOs;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    /// <summary>
    /// Mock AI controller — simulates the Python AI service during development.
    /// Mirrors the exact request/response contract of the real quiz generation endpoint.
    /// To switch to the real service: update AIService:BaseURL and AIService:McqGeneratePath
    /// in appsettings.Development.json.
    /// </summary>
    [Route("api/mock-ai")]
    [ApiController]
    public class MockAIController : ControllerBase
    {
        // Fixed seed so results are reproducible per run
        private static readonly Random _rng = new(42);

        private static readonly string[] BloomLevels =
            { "remember", "understand", "apply", "analyze", "evaluate", "create" };

        private static readonly string[] ChunkTypeQuestionTemplates = new[]
        {
            "Which of the following best describes {concept} as described in the course material?",
            "Based on the provided content, what is true about {concept}?",
            "According to the material, which statement correctly explains {concept}?",
            "What does the course content state about {concept}?"
        };

        private static readonly string[] QuizChunkTypes =
            { "definition", "conceptual", "procedural", "example", "comparison", "application" };

        // ── POST /api/mock-ai/quiz/generate ─────────────────────────────────────
        // Mirrors: POST {AIService:BaseURL}/{AIService:McqGeneratePath}
        // Contract: McqGenerateRequest → McqGenerateResponse

        /// <summary>
        /// Mock MCQ generation — generates one question per quiz chunk.
        /// Accepts the same McqGenerateRequest the real Python service expects.
        /// </summary>
        [HttpPost("quiz/generate")]
        [ProducesResponseType<McqGenerateResponse>(200)]
        [ProducesResponseType(400)]
        public IActionResult GenerateQuiz([FromBody] McqGenerateRequest request)
        {
            if (request?.Chunks == null || !request.Chunks.Any())
                return BadRequest("No chunks provided.");

            if (request.NumberOfQuestions <= 0)
                return BadRequest("Number of questions must be greater than zero.");

            var questions = new List<McqGeneratedQuestion>();

            for (int questionIndex = 0; questionIndex < request.NumberOfQuestions; questionIndex++)
            {
                var chunk = request.Chunks[questionIndex % request.Chunks.Count];
                var variantNumber = (questionIndex / request.Chunks.Count) + 1;
                // ── Derive concept ────────────────────────────────────────────
                var concept = chunk.Concepts?.FirstOrDefault()
                              ?? chunk.Keywords?.FirstOrDefault()
                              ?? TruncateWords(chunk.ChunkText, 4);

                // ── Bloom level ───────────────────────────────────────────────
                var bloomLevel = !string.IsNullOrWhiteSpace(chunk.BloomLevel)
                    ? chunk.BloomLevel
                    : BloomLevels[_rng.Next(BloomLevels.Length)];

                // ── Build question text using context if available ─────────────
                // Context sentences give richer question stems when present
                var contextHint = !string.IsNullOrWhiteSpace(chunk.ContextPrevSentence)
                    ? $" (Context: {TruncateWords(chunk.ContextPrevSentence, 8)})"
                    : string.Empty;

                var templateIndex = HashCode.Combine(chunk.ChunkId, questionIndex) & int.MaxValue;
                var questionTemplate =
                    ChunkTypeQuestionTemplates[templateIndex % ChunkTypeQuestionTemplates.Length];

                var questionText = questionTemplate.Replace("{concept}", $"'{concept}'") +
                                   contextHint +
                                   (variantNumber > 1 ? $" (Variant {variantNumber})" : string.Empty);

                // ── Build 4 options ───────────────────────────────────────────
                // Option 0 (index) is always the correct one — it is derived
                // directly from the chunk text for maximum realism.
                var correctText = BuildCorrectOption(chunk.ChunkText, concept);

                var distractors = BuildDistractors(chunk, concept);

                // Collect all 4 texts: correct first, then 3 distractors
                var optionTexts = new[] { correctText, distractors[0], distractors[1], distractors[2] };

                // Fisher-Yates shuffle so correct answer is not always label 'A'
                var positions = new[] { 0, 1, 2, 3 };
                for (int i = 3; i > 0; i--)
                {
                    int j = _rng.Next(i + 1);
                    (positions[i], positions[j]) = (positions[j], positions[i]);
                }

                char[] labels = { 'A', 'B', 'C', 'D' };
                char correctLabel = 'A';
                var options = new List<McqGeneratedOption>();

                for (int i = 0; i < 4; i++)
                {
                    options.Add(new McqGeneratedOption
                    {
                        Label = labels[i],
                        Text = optionTexts[positions[i]]
                    });
                    // positions[i] == 0 means this slot holds the correct text
                    if (positions[i] == 0)
                        correctLabel = labels[i];
                }

                // ── Build explanation using next sentence context if available ─
                var explanation = BuildExplanation(chunk, concept, bloomLevel);

                questions.Add(new McqGeneratedQuestion
                {
                    QuestionText = questionText,
                    CorrectOption = correctLabel,
                    Explanation = explanation,
                    Concept = concept,
                    BloomLevel = bloomLevel,
                    ChunkId = chunk.ChunkId,
                    Options = options
                });
            }

            return Ok(new McqGenerateResponse { Questions = questions });
        }

        // POST /api/mock-ai/quiz/process
        // Mirrors: POST {AIService:BaseURL}/{AIService:QuizChunkingPath}
        // Contract: AIChunkRequest -> List<QuizChunkResponse>

        /// <summary>
        /// Mock quiz chunking - creates quiz-ready chunks from the document metadata.
        /// Accepts the same AIChunkRequest the real Python service expects.
        /// </summary>
        [HttpPost("quiz/process")]
        [ProducesResponseType<List<QuizChunkResponse>>(200)]
        [ProducesResponseType(400)]
        public IActionResult GenerateQuizChunks([FromBody] AIChunkRequest request)
        {
            if (request == null || string.IsNullOrWhiteSpace(request.DocumentPath))
                return BadRequest("Document path is required.");

            var sourceName = GetDocumentTopic(request.DocumentPath);
            var documentType = string.IsNullOrWhiteSpace(request.DocumentType)
                ? "document"
                : request.DocumentType.Trim().TrimStart('.');

            var chunks = new List<QuizChunkResponse>();

            for (int i = 0; i < 8; i++)
            {
                var chunkType = QuizChunkTypes[i % QuizChunkTypes.Length];
                var bloomLevel = BloomLevels[i % BloomLevels.Length];
                var concept = BuildConceptName(sourceName, chunkType, i);
                var keywords = BuildQuizKeywords(sourceName, chunkType, documentType, i);

                chunks.Add(new QuizChunkResponse
                {
                    ChunkIndex = i,
                    ChunkText = BuildQuizChunkText(sourceName, concept, chunkType, documentType, i),
                    ContextPrevSentence = i == 0
                        ? $"The {sourceName} material begins by framing the main learning goals."
                        : $"The previous section introduced prerequisite ideas for {concept}.",
                    ContextNextSentence = i == 7
                        ? $"The {sourceName} material closes by connecting these ideas to review questions."
                        : $"The next section expands {concept} with a worked learning example.",
                    SemanticScore = Math.Round(0.92 - (i * 0.015), 3),
                    QualityScore = Math.Round(0.88 - (i * 0.01), 3),
                    BloomLevel = bloomLevel,
                    ChunkType = chunkType,
                    Concepts = new List<string>
                    {
                        concept,
                        $"{sourceName} {chunkType}",
                        $"{bloomLevel} skill"
                    },
                    Keywords = keywords
                });
            }

            return Ok(chunks);
        }

        // ── Private helpers ──────────────────────────────────────────────────────

        /// <summary>Builds the correct option text directly from the chunk body.</summary>
        private static string BuildCorrectOption(string chunkText, string concept)
        {
            var excerpt = TruncateWords(chunkText, 12);
            return $"{concept}: {excerpt}.";
        }

        /// <summary>
        /// Builds 3 plausible but incorrect distractors.
        /// Uses context sentences and keyword permutations when available.
        /// </summary>
        private static string[] BuildDistractors(McqChunkInput chunk, string concept)
        {
            var words = chunk.ChunkText.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            var keywords = chunk.Keywords ?? new List<string>();
            var concepts = chunk.Concepts ?? new List<string>();

            // Distractor 1: negation pattern
            var d1 = $"{concept} is not related to {PickWords(words, 3, startOffset: 5)}.";

            // Distractor 2: swap concept with an alternate keyword/concept if available
            var altConcept = concepts.Skip(1).FirstOrDefault()
                             ?? keywords.Skip(1).FirstOrDefault()
                             ?? PickWords(words, 2, startOffset: 10);
            var d2 = $"{altConcept} is the primary explanation for {PickWords(words, 3, startOffset: 2)}.";

            // Distractor 3: uses next-sentence context (out-of-scope misdirection) if present
            var d3Source = !string.IsNullOrWhiteSpace(chunk.ContextNextSentence)
                ? TruncateWords(chunk.ContextNextSentence, 10)
                : PickWords(words, 4, startOffset: 8);
            var d3 = $"According to the material, {concept} always requires {d3Source}.";

            return new[] { d1, d2, d3 };
        }

        /// <summary>Builds a pedagogically-framed explanation citing the source text.</summary>
        private static string BuildExplanation(McqChunkInput chunk, string concept, string bloomLevel)
        {
            var excerpt = TruncateWords(chunk.ChunkText, 20);

            var contextNote = !string.IsNullOrWhiteSpace(chunk.ContextPrevSentence)
                ? $" The surrounding context states: \"{TruncateWords(chunk.ContextPrevSentence, 10)}\"."
                : string.Empty;

            return $"The source material states: \"{excerpt}\".{contextNote} " +
                   $"This question targets the '{bloomLevel}' level of Bloom's Taxonomy " +
                   $"for the concept '{concept}'.";
        }

        /// <summary>Returns the first N words of a string.</summary>
        private static string TruncateWords(string? text, int wordCount)
        {
            if (string.IsNullOrWhiteSpace(text)) return "this topic";
            var words = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            return string.Join(' ', words.Take(wordCount)).TrimEnd('.', ',', ';', ':');
        }

        /// <summary>Picks N words from a word array starting at an offset (wraps safely).</summary>
        private static string PickWords(string[] words, int count, int startOffset)
        {
            if (words.Length == 0) return "external dependencies";
            int start = startOffset % words.Length;
            var picked = new List<string>();
            for (int i = 0; i < count; i++)
                picked.Add(words[(start + i) % words.Length]);
            return string.Join(' ', picked).TrimEnd('.', ',', ';', ':');
        }

        private static string GetDocumentTopic(string documentPath)
        {
            var path = documentPath.Split('?', '#')[0];
            var fileName = Path.GetFileNameWithoutExtension(path);

            if (string.IsNullOrWhiteSpace(fileName))
                fileName = "course material";

            var readable = fileName
                .Replace('_', ' ')
                .Replace('-', ' ')
                .Replace("%20", " ")
                .Trim();

            return string.IsNullOrWhiteSpace(readable) ? "course material" : readable;
        }

        private static string BuildConceptName(string sourceName, string chunkType, int index)
        {
            var focus = chunkType switch
            {
                "definition" => "core definition",
                "conceptual" => "main concept",
                "procedural" => "process steps",
                "example" => "worked example",
                "comparison" => "key comparison",
                "application" => "practical application",
                _ => "learning point"
            };

            return $"{sourceName} {focus} {index + 1}";
        }

        private static List<string> BuildQuizKeywords(
            string sourceName,
            string chunkType,
            string documentType,
            int index)
        {
            return new List<string>
            {
                sourceName,
                chunkType,
                documentType,
                $"section {index + 1}",
                "quiz"
            };
        }

        private static string BuildQuizChunkText(
            string sourceName,
            string concept,
            string chunkType,
            string documentType,
            int index)
        {
            return $"Section {index + 1} of the {documentType} source '{sourceName}' focuses on {concept}. " +
                   $"This {chunkType} chunk explains the idea, highlights the important terms, " +
                   "and gives enough context for generating one multiple choice question. " +
                   $"Learners should be able to recognize how {concept} is used in the lesson material.";
        }
    }
}
