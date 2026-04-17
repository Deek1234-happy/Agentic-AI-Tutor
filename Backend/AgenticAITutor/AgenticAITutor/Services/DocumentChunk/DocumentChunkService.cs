using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;
using Pgvector;

namespace AgenticAITutor.Services
{
    public class DocumentChunkService : IDocumentChunkService
    {
        private readonly IDocumentChunkRepository chunkRepository;
        private readonly IDocumentRepository documentRepository;
        private readonly HttpClient httpClient;
        private readonly IConfiguration configuration;

        public DocumentChunkService(IDocumentChunkRepository chunkRepository, 
            IDocumentRepository documentRepository, 
            IHttpClientFactory httpClientFactory, 
            IConfiguration configuration)
        {
            this.chunkRepository = chunkRepository;
            this.documentRepository = documentRepository;
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

            string? aiURL = $"{aiBaseURL.TrimEnd('/')}/{chunkingPath.TrimStart('/')}";

            //httpClient.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true");

            var response = await httpClient.PostAsJsonAsync(aiURL, aiRequest);
            if (!response.IsSuccessStatusCode)
            {
                string errorBody = await response.Content.ReadAsStringAsync();

                // Also, let's log the URL you sent so you can visually verify it's correct
                throw new Exception($"AI API Failed! Status: {response.StatusCode}. Sent URL: {aiRequest.DocumentPath}. AI Error Details: {errorBody}");
            }

            var aiChunks = await response.Content.ReadFromJsonAsync<List<AIChunkResponse>>();

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
                        PageStart = aiChunk.PageStart,
                        PageEnd = aiChunk.PageEnd,
                        Embedding = new Vector(aiChunk.Embedding),
                        CreatedAt = DateTime.Now
                    });
                }

                // Save all chunks to the database in one big batch
                await chunkRepository.AddRangeAsync(dbChunks);
            }
        }

        //public async Task ChunkDocumentAsync(DocumentChunkRequest chunkRequest)
        //{
        //    await mockedDocumentChunkService.ChunkDocumentAsync(chunkRequest);
        //}

        public async Task<List<DocumentChunkResponse>> GetDocumentChunksAsync(Guid documentId, Guid userId)
        {
            var chunks = await chunkRepository.GetByDocumentAsync(documentId, userId);
            var chunksResponse = chunks.Select(c => new DocumentChunkResponse
            {
                Id = c.Id,
                Text = c.ChunkText,
                Topic = c.Topic,
                Difficulty = c.Difficulty,
                TokenCount = c.TokenCount ?? 0,
                PageStart = c.PageStart ?? 0,
                PageEnd = c.PageEnd ?? 0,
                Embedding = c.Embedding
            }).ToList();

            return chunksResponse;
        }

    }
}
