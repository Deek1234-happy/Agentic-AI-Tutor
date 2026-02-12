using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;

namespace AgenticAITutor.Services
{
    public class DocumentChunkService : IDocumentChunkService
    {
        private readonly IDocumentChunkRepository chunkRepository;
        private MockedEmbeddings mockedDocumentChunkService;

        public DocumentChunkService(IDocumentChunkRepository chunkRepository)
        {
            this.chunkRepository = chunkRepository;
            this.mockedDocumentChunkService = new MockedEmbeddings(chunkRepository);
        }

        public async Task ChunkDocumentAsync(DocumentChunkRequest chunkRequest)
        {
            await mockedDocumentChunkService.ChunkDocumentAsync(chunkRequest);
        }

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
