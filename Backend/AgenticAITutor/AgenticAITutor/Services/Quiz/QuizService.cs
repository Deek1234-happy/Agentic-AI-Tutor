using AgenticAITutor.BackgroundJobs;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.Enums;
using AgenticAITutor.Repositories;
using Hangfire;
using System.Text.Json;

namespace AgenticAITutor.Services
{
    public class QuizService : IQuizService
    {
        private readonly IQuizRepository _quizRepo;
        private readonly IDocumentRepository _docRepo;
        private readonly ISubjectRepository _subjectRepo;
        private readonly IGenerationHashService _hashService;

        public QuizService(
            IQuizRepository quizRepo,
            IDocumentRepository docRepo,
            ISubjectRepository subjectRepo,
            IGenerationHashService hashService)
        {
            _quizRepo = quizRepo;
            _docRepo = docRepo;
            _subjectRepo = subjectRepo;
            _hashService = hashService;
        }

        // ── POST /api/Quiz/initiate ───────────────────────────────────────────

        public async Task<ServiceResponse<QuizInitiateResponse>> InitiateAsync(
            Guid userId, QuizInitiateRequest request)
        {
            var response = new ServiceResponse<QuizInitiateResponse>();

            // 1. Validate subject ownership
            var subject = await _subjectRepo.GetByIdAsync(request.SubjectId);
            if (subject == null || subject.UserId != userId)
            {
                response.Success = false;
                response.Message = "Subject not found or does not belong to you.";
                return response;
            }

            // 2. Validate all documents belong to user and are fully processed
            var docs = await _docRepo.GetDocumentsByIdsAsync(request.DocumentIds, userId);
            if (docs.Count != request.DocumentIds.Count)
            {
                response.Success = false;
                response.Message = "One or more documents were not found or do not belong to you.";
                return response;
            }

            var notReady = docs.Where(d => d.ProcessingStatus != DocumentProcessingStatus.COMPLETED.ToString() || d.QuizChunkingStatus != DocumentProcessingStatus.COMPLETED.ToString()).ToList();
            if (notReady.Any())
            {
                response.Success = false;
                response.Message = $"Document(s) not fully processed: {string.Join(", ", notReady.Select(d => d.Filename))}.";
                return response;
            }

            // 3. Compute deterministic hash
            var hash = _hashService.ComputeHash(userId, request.DocumentIds, request.NumberOfQuestions);

            // 4. Check for existing quiz with this hash
            var existing = await _quizRepo.GetByUserAndHashAsync(userId, hash);

            if (existing != null)
            {
                if (existing.Status == QuizStatus.READY.ToString())
                {
                    // Cache hit — reuse
                    response.Data = new QuizInitiateResponse
                    {
                        QuizId = existing.Id,
                        Status = existing.Status,
                        Message = "Quiz already exists." // Ready to start."
                    };
                    return response;
                }

                if (existing.Status == QuizStatus.GENERATING.ToString())
                {
                    // Already in progress — tell caller to keep polling
                    response.Success = false;
                    response.Message = "Quiz generation is already in progress.";
                    response.Data = new QuizInitiateResponse
                    {
                        QuizId = existing.Id,
                        Status = existing.Status,
                        Message = "Generation already in progress."
                    };
                    return response;
                }

                // FAILED — delete stale quiz and regenerate
                if (existing.Status == QuizStatus.FAILED.ToString())
                    await _quizRepo.DeleteAsync(existing);
            }

            // 5. Create new quiz row with GENERATING status
            var quiz = new Quiz
            {
                UserId = userId,
                SubjectId = request.SubjectId,
                GenerationHash = hash,
                Status = QuizStatus.GENERATING.ToString(),
                CreatedAt = DateTime.Now
            };

            await _quizRepo.AddAsync(quiz);

            // 6. Insert junction rows (quiz_documents)
            await _quizRepo.AddQuizDocumentsAsync(quiz.Id, request.DocumentIds);

            // 7. Enqueue Hangfire job
            BackgroundJob.Enqueue<QuizGenerationJob>(job => job.Execute(quiz.Id, request.NumberOfQuestions));

            response.Data = new QuizInitiateResponse
            {
                QuizId = quiz.Id,
                Status = quiz.Status,
                Message = "Quiz generation started."
            };
            response.Message = "Accepted.";
            return response;
        }

        // ── GET /api/Quiz/{quizId}/status ─────────────────────────────────────

        public async Task<ServiceResponse<QuizStatusResponse>> GetStatusAsync(Guid userId, Guid quizId)
        {
            var response = new ServiceResponse<QuizStatusResponse>();
            var quiz = await _quizRepo.GetByIdAsync(quizId);

            if (quiz == null || quiz.UserId != userId)
            {
                response.Success = false;
                response.Message = "Quiz not found.";
                return response;
            }

            response.Data = new QuizStatusResponse
            {
                QuizId = quiz.Id,
                Status = quiz.Status,
                QuestionCount = quiz.QuestionCount ?? 0,
                GeneratedAt = quiz.GeneratedAt
            };
            return response;
        }

        // ── GET /api/Quiz/{quizId}/start ──────────────────────────────────────

        public async Task<ServiceResponse<QuizStartResponse>> StartAsync(Guid userId, Guid quizId)
        {
            var response = new ServiceResponse<QuizStartResponse>();

            var quiz = await _quizRepo.GetByIdWithQuestionsAsync(quizId);
            if (quiz == null || quiz.UserId != userId)
            {
                response.Success = false;
                response.Message = "Quiz not found.";
                return response;
            }

            if (quiz.Status != QuizStatus.READY.ToString())
            {
                response.Success = false;
                response.Message = $"Quiz is not ready yet. Current status: {quiz.Status}.";
                return response;
            }

            if (!quiz.QuizQuestions.Any())
            {
                response.Success = false;
                response.Message = "Quiz has no questions.";
                return response;
            }

            // Create attempt
            var attemptCount = await _quizRepo.GetAttemptCountAsync(quizId, userId);
            var attempt = new QuizAttempt
            {
                QuizId = quizId,
                UserId = userId,
                AttemptNumber = attemptCount + 1,
                StartedAt = DateTime.Now
            };

            // Fisher-Yates shuffle seeded by attemptId hash
            // We generate the id first so we can use it as the seed
            attempt.Id = Guid.NewGuid();
            var rng = new Random(attempt.Id.GetHashCode());

            // Build the shuffle mapping: { questionId -> { shuffledLabel -> originalLabel } }
            var shuffleMapping = new Dictionary<string, Dictionary<string, string>>();
            var questionDtos = new List<QuizQuestionDto>();

            foreach (var question in quiz.QuizQuestions.OrderBy(q => q.SlotIndex))
            {
                var options = question.QuizOptions.ToList();

                // Shuffle the list indices using Fisher-Yates
                for (int i = options.Count - 1; i > 0; i--)
                {
                    int j = rng.Next(i + 1);
                    (options[i], options[j]) = (options[j], options[i]);
                }

                // Assign new labels A, B, C, D to shuffled options
                char[] labels = { 'A', 'B', 'C', 'D' };
                var questionMapping = new Dictionary<string, string>(); // shuffledLabel -> originalLabel
                var optionDtos = new List<QuizOptionDto>();

                for (int i = 0; i < options.Count; i++)
                {
                    char newLabel = labels[i];
                    char originalLabel = options[i].OptionLabel ?? labels[i];
                    questionMapping[newLabel.ToString()] = originalLabel.ToString();
                    optionDtos.Add(new QuizOptionDto { Label = newLabel, Text = options[i].OptionText });
                }

                shuffleMapping[question.Id.ToString()] = questionMapping;

                questionDtos.Add(new QuizQuestionDto
                {
                    Id = question.Id,
                    SlotIndex = question.SlotIndex ?? 0,
                    QuestionText = question.QuestionText,
                    BloomLevel = question.BloomLevel,
                    Concept = question.Concept,
                    Options = optionDtos
                });
            }

            // Persist the shuffle mapping on the attempt
            attempt.ShuffleMapping = JsonSerializer.Serialize(shuffleMapping);
            await _quizRepo.AddAttemptAsync(attempt);

            response.Data = new QuizStartResponse
            {
                QuizId = quizId,
                AttemptId = attempt.Id,
                AttemptNumber = attempt.AttemptNumber,
                Questions = questionDtos
            };
            return response;
        }

        // ── POST /api/Quiz/{quizId}/submit ────────────────────────────────────

        public async Task<ServiceResponse<QuizSubmitResponse>> SubmitAsync(
            Guid userId, Guid quizId, QuizSubmitRequest request)
        {
            var response = new ServiceResponse<QuizSubmitResponse>();

            var attempt = await _quizRepo.GetAttemptByIdAsync(request.AttemptId);
            if (attempt == null || attempt.UserId != userId || attempt.QuizId != quizId)
            {
                response.Success = false;
                response.Message = "Attempt not found.";
                return response;
            }

            // Idempotency: already submitted
            if (attempt.FinishedAt.HasValue)
            {
                response.Data = new QuizSubmitResponse
                {
                    AttemptId = attempt.Id,
                    Score = attempt.Score ?? 0,
                    FinishedAt = attempt.FinishedAt.Value,
                    TotalCount = request.Answers.Count
                };
                response.Message = "Already submitted.";
                return response;
            }

            // Deserialize shuffle mapping: { questionId -> { shuffledLabel -> originalLabel } }
            var shuffleMapping = string.IsNullOrWhiteSpace(attempt.ShuffleMapping)
                ? new Dictionary<string, Dictionary<string, string>>()
                : JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, string>>>(attempt.ShuffleMapping)
                  ?? new Dictionary<string, Dictionary<string, string>>();

            // Load correct options for the submitted questions
            var questionIds = request.Answers.Select(a => a.QuestionId).ToList();
            var questions = await _quizRepo.GetByIdWithQuestionsAsync(quizId);

            var questionMap = questions?.QuizQuestions
                .Where(q => questionIds.Contains(q.Id))
                .ToDictionary(q => q.Id, q => q.CorrectOption)
                ?? new Dictionary<Guid, char>();

            int correctCount = 0;
            var answers = new List<QuizAnswer>();

            foreach (var item in request.Answers)
            {
                // Reverse-map: shuffled label → original label
                char originalSelected = item.SelectedOption;
                if (shuffleMapping.TryGetValue(item.QuestionId.ToString(), out var qMap))
                {
                    if (qMap.TryGetValue(item.SelectedOption.ToString(), out var originalStr)
                        && originalStr.Length == 1)
                        originalSelected = originalStr[0];
                }

                bool isCorrect = questionMap.TryGetValue(item.QuestionId, out var correctOption)
                    && char.ToUpper(originalSelected) == char.ToUpper(correctOption);

                if (isCorrect) correctCount++;

                answers.Add(new QuizAnswer
                {
                    AttemptId = attempt.Id,
                    QuestionId = item.QuestionId,
                    SelectedOption = originalSelected, // store original label
                    IsCorrect = isCorrect
                });
            }

            await _quizRepo.AddAnswersAsync(answers);

            double score = request.Answers.Count > 0
                ? Math.Round((double)correctCount / request.Answers.Count * 100, 2)
                : 0;

            attempt.Score = score;
            attempt.FinishedAt = DateTime.Now;
            await _quizRepo.UpdateAttemptAsync(attempt);

            response.Data = new QuizSubmitResponse
            {
                AttemptId = attempt.Id,
                Score = score,
                CorrectCount = correctCount,
                TotalCount = request.Answers.Count,
                FinishedAt = attempt.FinishedAt.Value
            };
            return response;
        }

        // ── GET /api/Quiz/{quizId}/attempts ───────────────────────────────────

        public async Task<ServiceResponse<List<QuizAttemptSummary>>> GetAttemptsAsync(
            Guid userId, Guid quizId)
        {
            var response = new ServiceResponse<List<QuizAttemptSummary>>();

            var quiz = await _quizRepo.GetByIdAsync(quizId);
            if (quiz == null || quiz.UserId != userId)
            {
                response.Success = false;
                response.Message = "Quiz not found.";
                return response;
            }

            var attempts = await _quizRepo.GetAttemptsByQuizAndUserAsync(quizId, userId);
            response.Data = attempts.Select(a => new QuizAttemptSummary
            {
                AttemptId = a.Id,
                AttemptNumber = a.AttemptNumber,
                Score = a.Score,
                StartedAt = a.StartedAt,
                FinishedAt = a.FinishedAt
            }).ToList();

            return response;
        }

        // ── GET /api/Quiz/attempt/{attemptId}/review ──────────────────────────

        public async Task<ServiceResponse<QuizReviewResponse>> GetReviewAsync(
            Guid userId, Guid attemptId)
        {
            var response = new ServiceResponse<QuizReviewResponse>();

            var attempt = await _quizRepo.GetAttemptWithAnswersAsync(attemptId);
            if (attempt == null || attempt.UserId != userId)
            {
                response.Success = false;
                response.Message = "Attempt not found.";
                return response;
            }

            if (!attempt.FinishedAt.HasValue)
            {
                response.Success = false;
                response.Message = "This attempt has not been submitted yet.";
                return response;
            }

            var answerMap = attempt.QuizAnswers
                .ToDictionary(a => a.QuestionId, a => a);

            int totalCount = attempt.QuizAnswers.Count;
            int correctCount = attempt.QuizAnswers.Count(a => a.IsCorrect == true);

            var questionDtos = attempt.QuizAnswers
                .OrderBy(ans => ans.Question.SlotIndex)
                .Select(ans =>
            {
                var q = ans.Question;
                return new QuizReviewQuestionDto
                {
                    Id = q.Id,
                    QuestionText = q.QuestionText,
                    Explanation = q.Explanation,
                    BloomLevel = q.BloomLevel,
                    Concept = q.Concept,
                    CorrectOption = q.CorrectOption,
                    SelectedOption = ans.SelectedOption,
                    IsCorrect = ans.IsCorrect ?? false,
                    Options = q.QuizOptions
                        .OrderBy(o => o.OptionLabel)
                        .Select(o => new QuizOptionDto
                        {
                            Label = o.OptionLabel ?? ' ',
                            Text = o.OptionText
                        }).ToList()
                };
            }).ToList();

            response.Data = new QuizReviewResponse
            {
                AttemptId = attempt.Id,
                QuizId = attempt.QuizId ?? Guid.Empty,
                Score = attempt.Score ?? 0,
                CorrectCount = correctCount,
                TotalCount = totalCount,
                StartedAt = attempt.StartedAt,
                FinishedAt = attempt.FinishedAt,
                Questions = questionDtos
            };

            return response;
        }

        // ── GET /api/Quiz/history ─────────────────────────────────────────────

        public async Task<ServiceResponse<List<QuizHistoryItem>>> GetHistoryAsync(
            Guid userId, QuizHistoryFilter filter)
        {
            var response = new ServiceResponse<List<QuizHistoryItem>>();

            var (items, _) = await _quizRepo.GetUserQuizHistoryAsync(
                userId, filter.SubjectId, filter.Status, filter.Page, filter.PageSize);

            response.Data = MapToHistoryItems(items);
            return response;
        }

        // ── GET /api/Quiz/subject/{subjectId} ─────────────────────────────────

        public async Task<ServiceResponse<List<QuizHistoryItem>>> GetBySubjectAsync(
            Guid userId, Guid subjectId)
        {
            var response = new ServiceResponse<List<QuizHistoryItem>>();
            var quizzes = await _quizRepo.GetBySubjectAsync(userId, subjectId);
            response.Data = MapToHistoryItems(quizzes);
            return response;
        }

        // ── Private helpers ───────────────────────────────────────────────────

        private static List<QuizHistoryItem> MapToHistoryItems(List<Quiz> quizzes)
            => quizzes.Select(q => new QuizHistoryItem
            {
                QuizId = q.Id,
                Status = q.Status,
                SubjectId = q.SubjectId,
                SubjectName = q.Subject?.Name,
                QuestionCount = q.QuestionCount ?? 0,
                CreatedAt = q.CreatedAt,
                AttemptCount = q.QuizAttempts.Count,
                BestScore = q.QuizAttempts.Any()
                    ? q.QuizAttempts.Max(a => a.Score)
                    : null
            }).ToList();
    }
}
