using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.Enums;
using AgenticAITutor.Repositories;
using AgenticAITutor.Services;

namespace AgenticAITutor.BackgroundJobs
{
    public class DocumentChunkingJob
    {
        private readonly IDocumentChunkService chunkService;
        private readonly IDocumentRepository documentRepository;

        public DocumentChunkingJob(IDocumentChunkService chunkService, IDocumentRepository documentRepository)
        {
            this.chunkService = chunkService;
            this.documentRepository = documentRepository;
        }

        public async Task ChunkDocument(Guid documentId)
        {
            var document = await documentRepository.GetByIdAsync(documentId);
            if (document == null)
                return;
            try
            {
                document.ProcessingStatus = DocumentProcessingStatus.PROCESSING.ToString();
                await documentRepository.UpdateAsync(document);

                var request = new DocumentChunkRequest
                {
                    DocumentId = documentId,
                    UserId = document.UserId,
                    SubjectId = document.SubjectId,
                    DocumentPath = document.StoragePath
                };

                await chunkService.ChunkDocumentAsync(request);

                document.ProcessingStatus = DocumentProcessingStatus.COMPLETED.ToString();
                await documentRepository.UpdateAsync(document);
            }
            catch (Exception ex)
            {
                document.ProcessingStatus = DocumentProcessingStatus.FAILED.ToString();
                await documentRepository.UpdateAsync(document);

                Console.WriteLine($"Error Processing Document {documentId}: {ex.Message}");
            }
        }
    }
}
