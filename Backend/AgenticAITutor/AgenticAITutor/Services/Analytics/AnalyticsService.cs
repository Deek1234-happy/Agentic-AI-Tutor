using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AgenticAITutor.Models.DTOs.Analytics;
using AgenticAITutor.Repositories.Analytics;

namespace AgenticAITutor.Services.Analytics;

public class AnalyticsService : IAnalyticsService
{
    private readonly IAnalyticsRepository _analyticsRepository;

    public AnalyticsService(IAnalyticsRepository analyticsRepository)
    {
        _analyticsRepository = analyticsRepository;
    }

    public async Task<ProgressDashboardResponseDto> GetProgressDashboardAsync(Guid userId)
    {
        var attempts = await _analyticsRepository.GetUserAttemptsWithDetailsAsync(userId);
        
        var response = new ProgressDashboardResponseDto();

        if (attempts == null || !attempts.Any())
        {
            return response;
        }

        // Top-level KPIs
        response.TotalQuizzes = attempts.Count;
        
        var subjects = attempts.Where(a => a.Quiz != null && a.Quiz.Subject != null)
                               .Select(a => a.Quiz.Subject.Id)
                               .Distinct()
                               .ToList();
        response.ActiveSubjects = subjects.Count;

        var validScores = attempts.Where(a => a.Score.HasValue).Select(a => a.Score.Value).ToList();
        response.OverallMastery = validScores.Any() ? (int)Math.Round(validScores.Average()) : 0;

        // Monthly Graph (Last 6 months)
        var sixMonthsAgo = DateTime.UtcNow.AddMonths(-6);
        var recentAttempts = attempts.Where(a => a.FinishedAt.HasValue && a.FinishedAt.Value >= sixMonthsAgo && a.Score.HasValue).ToList();
        
        var monthlyData = recentAttempts
            .GroupBy(a => new DateTime(a.FinishedAt.Value.Year, a.FinishedAt.Value.Month, 1))
            .OrderBy(g => g.Key)
            .Select(g => new MonthlyPerformanceDto
            {
                Month = g.Key.ToString("MMM"),
                Score = (int)Math.Round(g.Average(a => a.Score.Value))
            })
            .ToList();

        response.MonthlyPerformance = monthlyData;

        // Subject Progress
        var subjectGroups = attempts.Where(a => a.Quiz != null && a.Quiz.Subject != null)
            .GroupBy(a => a.Quiz.Subject.Name);
            
        foreach(var g in subjectGroups)
        {
            var avgScore = g.Where(a => a.Score.HasValue).Any() ? (int)Math.Round(g.Where(a => a.Score.HasValue).Average(a => a.Score.Value)) : 0;
            var quizzesCount = g.Count();
            var studyTimeHours = quizzesCount * 15.0 / 60.0;
            
            response.SubjectProgress.Add(new SubjectProgressDto
            {
                Subject = g.Key,
                Mastery = avgScore,
                Quizzes = quizzesCount,
                StudyTime = $"{studyTimeHours:0.1}h" // Format as X.Xh
            });
        }

        // Keep weak-topic accuracy scoped to the subject so practice uses the
        // same subject's source material and later attempts can be compared.
        var conceptAnswers = attempts
            .SelectMany(attempt => attempt.QuizAnswers.Select(answer => new
            {
                Attempt = attempt,
                Answer = answer,
                Subject = attempt.Quiz?.Subject,
                Concept = answer.Question?.Concept?.Trim()
            }))
            .Where(item => item.Answer.IsCorrect.HasValue
                && item.Subject != null
                && !string.IsNullOrWhiteSpace(item.Concept))
            .GroupBy(item => new
            {
                SubjectId = item.Subject!.Id,
                ConceptKey = item.Concept!.ToUpperInvariant()
            })
            .Select(group => new
            {
                Answers = group.ToList(),
                First = group.First(),
                Incorrect = group.Where(item => item.Answer.IsCorrect == false).ToList()
            })
            .Where(group => group.Incorrect.Count > 0)
            .OrderByDescending(group => group.Incorrect.Count)
            .Take(5);

        foreach (var group in conceptAnswers)
        {
            var correctCount = group.Answers.Count(item => item.Answer.IsCorrect == true);
            var questionCount = group.Answers.Count;
            var mostRecentMistake = group.Incorrect
                .OrderByDescending(item => item.Attempt.FinishedAt)
                .First();
            var recentMistakes = group.Incorrect
                .Where(item => item.Attempt.Id == mostRecentMistake.Attempt.Id)
                .ToList();

            response.WeakConcepts.Add(new ConceptMasteryDto
            {
                ConceptName = group.First.Concept!,
                ErrorCount = group.Incorrect.Count,
                CorrectCount = correctCount,
                QuestionCount = questionCount,
                Accuracy = (int)Math.Round((double)correctCount / questionCount * 100),
                SubjectId = group.First.Subject!.Id,
                SubjectName = group.First.Subject.Name,
                ReviewAttemptId = mostRecentMistake.Attempt.Id,
                SourceDocumentIds = recentMistakes
                    .Where(item => item.Answer.Question.Chunk?.DocumentId.HasValue == true)
                    .Select(item => item.Answer.Question.Chunk!.DocumentId!.Value)
                    .Distinct()
                    .ToList(),
                SourceChunkIds = recentMistakes
                    .Where(item => item.Answer.Question.ChunkId.HasValue)
                    .Select(item => item.Answer.Question.ChunkId!.Value)
                    .Distinct()
                    .ToList()
            });
        }

        return response;
    }
}
