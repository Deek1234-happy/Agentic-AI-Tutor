using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public class QuizAIClient : IQuizAIClient
    {
        private readonly HttpClient _httpClient;
        private readonly IConfiguration _configuration;
        private readonly ILogger<QuizAIClient> _logger;

        public QuizAIClient(
            IHttpClientFactory httpClientFactory,
            IConfiguration configuration,
            ILogger<QuizAIClient> logger)
        {
            _httpClient = httpClientFactory.CreateClient("QuizAIClient");
            _configuration = configuration;
            _logger = logger;
        }

        public async Task<McqGenerateResponse> GenerateQuestionsAsync(McqGenerateRequest request)
        {
            var aiBaseUrl = _configuration["AIService:BaseURL"]
                ?? throw new InvalidOperationException("AIService:BaseURL is not configured.");

            var mcqPath = _configuration["AIService:McqGeneratePath"]
                ?? "quiz/generate";

            var url = $"{aiBaseUrl.TrimEnd('/')}/{mcqPath.TrimStart('/')}";

            // Polly retry is applied via the named HttpClient in Program.cs.
            // This method simply executes the request.
            var response = await _httpClient.PostAsJsonAsync(url, request);

            if (!response.IsSuccessStatusCode)
            {
                var errorBody = await response.Content.ReadAsStringAsync();
                _logger.LogError(
                    "Quiz AI service returned {StatusCode}. URL: {Url}. Body: {Body}",
                    response.StatusCode, url, errorBody);
                throw new HttpRequestException(
                    $"Quiz AI service failed with status {response.StatusCode}: {errorBody}");
            }

            var result = await response.Content.ReadFromJsonAsync<McqGenerateResponse>();
            if (result == null)
                throw new InvalidOperationException("Quiz AI service returned an empty or invalid response.");

            return result;
        }
    }
}
