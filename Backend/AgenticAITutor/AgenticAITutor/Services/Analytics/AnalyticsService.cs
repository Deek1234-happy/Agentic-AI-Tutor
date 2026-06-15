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

        // Weak Concepts
        var allAnswers = attempts.SelectMany(a => a.QuizAnswers).Where(qa => qa.IsCorrect == false).ToList();
        
        var conceptCounts = allAnswers
            .Where(qa => qa.Question != null && !string.IsNullOrEmpty(qa.Question.Concept))
            .GroupBy(qa => qa.Question.Concept)
            .Select(g => new ConceptMasteryDto
            {
                ConceptName = g.Key,
                ErrorCount = g.Count()
            })
            .OrderByDescending(c => c.ErrorCount)
            .Take(5)
            .ToList();
            
        response.WeakConcepts = conceptCounts;

        return response;
    }
}
