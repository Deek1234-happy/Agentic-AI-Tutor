using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IDocumentChunkService
    {
        Task ChunkDocumentAsync(DocumentChunkRequest chunkRequest);
        Task<List<DocumentChunkResponse>> GetDocumentChunksAsync(Guid documentId, Guid userId);
        Task KGChunkDocumentAsync(KGChunkRequest kGChunkRequest);
    }
}
