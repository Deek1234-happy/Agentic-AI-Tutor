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

                // Console.WriteLine($"Error Processing Document {documentId}: {ex.Message}");
                throw new Exception($"Chunking failed for Document {documentId}. Error: {ex.Message}", ex);
            }
        }
        public async Task KGChunkDocument (Guid documentId)
        {
            var document = await documentRepository.GetByIdAsync(documentId);
            if (document == null)
                return;

            if (document.ProcessingStatus != DocumentProcessingStatus.COMPLETED.ToString())
            {
                throw new InvalidOperationException($"Cannot start KG chunking. Document processing status is {document.ProcessingStatus}. Expected COMPLETED.");
            }

            try
            {
                document.KgStatus = KGChunkingStatus.PROCESSING.ToString();
                await documentRepository.UpdateAsync(document);


                KGChunkRequest kGChunkRequest = new KGChunkRequest { DocumentId = documentId };

                await chunkService.KGChunkDocumentAsync(kGChunkRequest);

                document.KgStatus = KGChunkingStatus.COMPLETED.ToString();
                await documentRepository.UpdateAsync(document);
            }
            catch (Exception ex)
            {
                document.KgStatus = KGChunkingStatus.FAILED.ToString();
                await documentRepository.UpdateAsync(document);

                // Console.WriteLine($"Error Processing Document {documentId}: {ex.Message}");
                throw new Exception($"KGChunking failed for Document {documentId}. Error: {ex.Message}", ex);
            }
        }
    }
}
