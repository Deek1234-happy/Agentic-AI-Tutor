using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IQuizAIClient
    {
        /// <summary>
        /// Sends chunks to the Python MCQ generation endpoint and returns
        /// the generated questions. Uses Polly for 3 retries with 120s timeout.
        /// </summary>
        Task<McqGenerateResponse> GenerateQuestionsAsync(McqGenerateRequest request);
    }
}
