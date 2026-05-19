using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.Enums;
using AgenticAITutor.Repositories;
using AgenticAITutor.Services;
using Hangfire;

namespace AgenticAITutor.BackgroundJobs
{
    public class QuizGenerationJob
    {
        private readonly IQuizRepository _quizRepo;
        private readonly IDocumentChunkRepository _chunkRepo;
        private readonly IQuizAIClient _aiClient;
        private readonly ILogger<QuizGenerationJob> _logger;

        public QuizGenerationJob(
            IQuizRepository quizRepo,
            IDocumentChunkRepository chunkRepo,
            IQuizAIClient aiClient,
            ILogger<QuizGenerationJob> logger)
        {
            _quizRepo = quizRepo;
            _chunkRepo = chunkRepo;
            _aiClient = aiClient;
            _logger = logger;
        }

        /// <summary>
        /// Main generation job. Runs completely outside the HTTP request.
        /// [DisableConcurrentExecution] prevents two workers from generating
        /// the same quiz simultaneously.
        /// [AutomaticRetry(Attempts = 0)] disables Hangfire's auto-retry because
        /// failure is handled explicitly by setting Status = FAILED.
        /// </summary>
        [DisableConcurrentExecution(60 * 60)]
        [AutomaticRetry(Attempts = 0)]
        public async Task Execute(Guid quizId)
        {
            _logger.LogInformation("QuizGenerationJob started for QuizId: {QuizId}", quizId);

            var quiz = await _quizRepo.GetByIdAsync(quizId);
            if (quiz == null)
            {
                _logger.LogWarning("QuizGenerationJob: Quiz {QuizId} not found. Aborting.", quizId);
                return;
            }

            try
            {
                // 1. Fetch the quiz with its documents so we know which doc IDs to use
                var quizWithDocs = await _quizRepo.GetByIdWithDocumentsAsync(quizId);
                var documentIds = quizWithDocs?.Documents.Select(d => d.Id).ToList()
                    ?? new List<Guid>();

                if (!documentIds.Any())
                {
                    throw new InvalidOperationException("Quiz has no associated documents.");
                }

                // 2. Fetch all chunks for these documents
                var allChunks = new List<DocumentChunk>();
                foreach (var docId in documentIds)
                {
                    // UserId is nullable on DocumentChunk; quiz.UserId carries it
                    var chunks = await _chunkRepo.GetByDocumentAsync(docId, quiz.UserId ?? Guid.Empty);
                    allChunks.AddRange(chunks);
                }

                if (!allChunks.Any())
                {
                    throw new InvalidOperationException("No chunks found for the selected documents.");
                }

                // 3. Build the MCQ generation request
                var mcqRequest = new McqGenerateRequest
                {
                    Chunks = allChunks.Select(c => new McqChunkInput
                    {
                        ChunkId = c.Id,
                        Text = c.ChunkText,
                        BloomLevel = c.BloomLevel,
                        ChunkType = c.ChunkType,
                        Concepts = c.Concepts,
                        Keywords = c.Keywords
                    }).ToList()
                };

                // 4. Call Python AI service (Polly retries configured on HttpClient)
                _logger.LogInformation(
                    "Calling AI MCQ service with {ChunkCount} chunks for QuizId: {QuizId}",
                    mcqRequest.Chunks.Count, quizId);

                var aiResponse = await _aiClient.GenerateQuestionsAsync(mcqRequest);

                if (aiResponse.Questions == null || !aiResponse.Questions.Any())
                    throw new InvalidOperationException("AI service returned no questions.");

                // 5. Map AI response → DB entities
                var questions = new List<QuizQuestion>();
                int slot = 0;

                foreach (var aiQuestion in aiResponse.Questions)
                {
                    var question = new QuizQuestion
                    {
                        QuizId = quizId,
                        QuestionText = aiQuestion.QuestionText,
                        CorrectOption = aiQuestion.CorrectOption,
                        Explanation = aiQuestion.Explanation,
                        Concept = aiQuestion.Concept,
                        BloomLevel = aiQuestion.BloomLevel,
                        SlotIndex = slot++,
                        ChunkId = aiQuestion.ChunkId,  // primary source chunk
                        QuizOptions = aiQuestion.Options.Select(o => new QuizOption
                        {
                            OptionLabel = o.Label,
                            OptionText = o.Text
                        }).ToList()
                    };

                    // Citation chunks (many-to-many via quiz_citations junction)
                    if (aiQuestion.CitationChunkIds != null && aiQuestion.CitationChunkIds.Any())
                    {
                        foreach (var cId in aiQuestion.CitationChunkIds)
                        {
                            var chunk = allChunks.FirstOrDefault(c => c.Id == cId);
                            if (chunk != null)
                                question.Chunks.Add(chunk);
                        }
                    }

                    questions.Add(question);
                }

                // 6. Bulk save
                await _quizRepo.AddQuestionsWithOptionsAsync(questions);

                // 7. Mark quiz as READY
                quiz.Status = QuizStatus.READY.ToString();
                quiz.QuestionCount = questions.Count;
                quiz.GeneratedAt = DateTime.Now;
                await _quizRepo.UpdateAsync(quiz);

                _logger.LogInformation(
                    "QuizGenerationJob completed. {QuestionCount} questions saved for QuizId: {QuizId}",
                    questions.Count, quizId);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "QuizGenerationJob FAILED for QuizId: {QuizId}", quizId);

                quiz.Status = QuizStatus.FAILED.ToString();
                await _quizRepo.UpdateAsync(quiz);
            }
        }
    }
}
