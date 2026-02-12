using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;
using Pgvector;

namespace AgenticAITutor.Services
{
    public class MockedEmbeddings
    {
        private readonly IDocumentChunkRepository documentChunkRepository;

        public MockedEmbeddings(IDocumentChunkRepository documentChunkRepository)
        {
            this.documentChunkRepository = documentChunkRepository;
        }

        public async Task ChunkDocumentAsync(DocumentChunkRequest chunkRequest)
        {
            await Task.Delay(5000);
            var chunks = new List <DocumentChunk>();
            for(int i = 0; i < 5; i++)
            {
                DocumentChunk documentChunk = new DocumentChunk
                {
                    UserId = chunkRequest.UserId,
                    DocumentId = chunkRequest.DocumentId,
                    SubjectId = (chunkRequest.SubjectId == null || chunkRequest.SubjectId == Guid.Empty) ? null : chunkRequest.SubjectId,
                    ChunkText = $"[MOCK CONTENT {i}] This is a simulated paragraph extracted from the document. The AI would put real OCR text here.",
                    Topic = i % 2 == 0 ? "Advanced AI" : "Basics Of C#",
                    PageStart = i,
                    PageEnd = i,
                    TokenCount = 50,
                    Embedding = GenerateRandomVector(1536),
                    CreatedAt = DateTime.Now
                };
                chunks.Add(documentChunk);
            }
            await documentChunkRepository.AddRangeAsync(chunks);                

        }
        private Vector GenerateRandomVector(int dimensions)
        {
            var random = new Random();
            float[] vec = new float[dimensions];
            for (int i = 0; i < dimensions; i++)
            {
                vec[i] = (float)random.NextDouble();
            }
            return new Vector(vec);
        }
    }
}
