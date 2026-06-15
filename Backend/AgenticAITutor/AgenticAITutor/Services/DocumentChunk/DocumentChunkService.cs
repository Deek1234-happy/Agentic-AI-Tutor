using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;
using Microsoft.AspNetCore.Http.HttpResults;
using Pgvector;

namespace AgenticAITutor.Services
{
    public class DocumentChunkService : IDocumentChunkService
    {
        private readonly IDocumentChunkRepository chunkRepository;
        private readonly IDocumentRepository documentRepository;
        private readonly IQuizChunkRepository quizChunkRepository;
        private readonly HttpClient httpClient;
        private readonly IConfiguration configuration;

        public DocumentChunkService(IDocumentChunkRepository chunkRepository, 
            IDocumentRepository documentRepository,
            IQuizChunkRepository quizChunkRepository,
            IHttpClientFactory httpClientFactory, 
            IConfiguration configuration)
        {
            this.chunkRepository = chunkRepository;
            this.documentRepository = documentRepository;
            this.quizChunkRepository = quizChunkRepository;
            this.httpClient = httpClientFactory.CreateClient(nameof(DocumentChunkService));
            this.configuration = configuration;
        }

        public async Task ChunkDocumentAsync(DocumentChunkRequest chunkRequest)
        {
            var document = await documentRepository.GetByIdAsync(chunkRequest.DocumentId);
            if (document == null)
                throw new Exception("Document Not Found");
            AIChunkRequest aiRequest = new AIChunkRequest
            {
                DocumentPath = $"{configuration["AppConfig:BaseURL"]}/{document.StoragePath}",
                DocumentType = document.FileType
            };


            string? aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";

            string? chunkingPath = configuration["AIService:ChunkingPath"] ?? "extract/embed";
            string? chunkingUrl = $"{aiBaseURL.TrimEnd('/')}/{chunkingPath.TrimStart('/')}";

            //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");

            var chunkingResponse = await httpClient.PostAsJsonAsync(chunkingUrl, aiRequest);
            if (!chunkingResponse.IsSuccessStatusCode)
            {
                string errorBody = await chunkingResponse.Content.ReadAsStringAsync();
                throw new Exception($"AI API Failed! Status: {chunkingResponse.StatusCode}. Sent URL: {aiRequest.DocumentPath}. AI Error Details: {errorBody}");
            }

            var aiChunks = await chunkingResponse.Content.ReadFromJsonAsync<List<AIChunkResponse>>();

            if (aiChunks != null && aiChunks.Any())
            {
                var dbChunks = new List<DocumentChunk>();

                foreach (var aiChunk in aiChunks)
                {
                    dbChunks.Add(new DocumentChunk
                    {
                        DocumentId = document.Id,
                        UserId = document.UserId,
                        SubjectId = document.SubjectId,
                        ChunkText = aiChunk.Text,
                        PageStart = aiChunk.PageStart ?? 0,
                        PageEnd = aiChunk.PageEnd ?? 0,
                        Embedding = new Vector(aiChunk.Embedding),
                        CreatedAt = DateTime.Now
                    });
                }

                // Save all chunks to the database in one big batch
                await chunkRepository.AddRangeAsync(dbChunks);
            }
        }

        public async Task QuizChunkDocumentAsync(DocumentChunkRequest chunkRequest)
        {
            var document = await documentRepository.GetByIdAsync(chunkRequest.DocumentId);
            if (document == null)
                throw new Exception("Document Not Found");
            AIChunkRequest aiRequest = new AIChunkRequest
            {
                DocumentPath = $"{configuration["AppConfig:BaseURL"]}/{document.StoragePath}",
                DocumentType = document.FileType
            };


            string? aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";

            string? quizChunkingPath = configuration["AIService:QuizChunkingPath"] ?? "quiz/process";
            string? chunkingUrl = $"{aiBaseURL.TrimEnd('/')}/{quizChunkingPath.TrimStart('/')}";

            //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");

            var quizChunkingResponse = await httpClient.PostAsJsonAsync(chunkingUrl, aiRequest);
            if (!quizChunkingResponse.IsSuccessStatusCode)
            {
                string errorBody = await quizChunkingResponse.Content.ReadAsStringAsync();
                throw new Exception($"AI API Failed! Status: {quizChunkingResponse.StatusCode}. Sent URL: {aiRequest.DocumentPath}. AI Error Details: {errorBody}");
            }

            var quizAiChunks = await quizChunkingResponse.Content.ReadFromJsonAsync<List<QuizChunkResponse>>();

            if (quizAiChunks != null && quizAiChunks.Any())
            {
                var dbChunks = new List<QuizChunk>();

                foreach (var quizAiChunk in quizAiChunks)
                {
                    dbChunks.Add(new QuizChunk
                    {
                        DocumentId = document.Id,
                        UserId = document.UserId,
                        SubjectId = document.SubjectId,
                        ChunkIndex = quizAiChunk.ChunkIndex,
                        ChunkText = quizAiChunk.ChunkText,
                        ContextPrevSentence = quizAiChunk.ContextPrevSentence,
                        ContextNextSentence = quizAiChunk.ContextNextSentence,
                        SemanticScore = quizAiChunk.SemanticScore,
                        QualityScore = quizAiChunk.QualityScore,
                        BloomLevel = quizAiChunk.BloomLevel,
                        ChunkType = quizAiChunk.ChunkType,
                        Concepts = quizAiChunk.Concepts,
                        Keywords = quizAiChunk.Keywords
                    });
                }

                // Save all chunks to the database in one big batch
                await quizChunkRepository.AddRangeAsync(dbChunks);
            }
        }

        public async Task KGChunkDocumentAsync (KGChunkRequest kGChunkRequest)
        {
            var document = await documentRepository.GetByIdAsync(kGChunkRequest.DocumentId);
            if (document == null)
                throw new Exception("Document Not Found");

            string? aiBaseURL = configuration["AIService:BaseURL"] ?? "https://localhost:8000";

            string? kgChunkingPath = configuration["AIService:KGChunkingPath"] ?? "chunk/";
            string? kgChunkingUrl = $"{aiBaseURL.TrimEnd('/')}/{kgChunkingPath.TrimStart('/')}";

            var kgChunkingResponse = await httpClient.PostAsJsonAsync(kgChunkingUrl, kGChunkRequest);
            if(!kgChunkingResponse.IsSuccessStatusCode)
            {
                string errorBody = await kgChunkingResponse.Content.ReadAsStringAsync();
                throw new Exception($"AI API Failed! Status: {kgChunkingResponse.StatusCode}. Sent ID: {kGChunkRequest.DocumentId}. AI Error Details: {errorBody}");

            }
            var kgStatus = await kgChunkingResponse.Content.ReadFromJsonAsync<KGChunkResponse>();

        }

        

        public async Task<List<DocumentChunkResponse>> GetDocumentChunksAsync(Guid documentId, Guid userId)
        {
            var chunks = await chunkRepository.GetByDocumentAsync(documentId, userId);
            var chunksResponse = chunks.Select(c => new DocumentChunkResponse
            {
                Id = c.Id,
                Text = c.ChunkText,
                PageStart = c.PageStart ?? 0,
                PageEnd = c.PageEnd ?? 0,
                Embedding = c.Embedding
            }).ToList();

            return chunksResponse;
        }

    }
}
