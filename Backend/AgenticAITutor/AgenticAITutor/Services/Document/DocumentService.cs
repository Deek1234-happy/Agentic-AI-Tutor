using AgenticAITutor.BackgroundJobs;
using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Models.Enums;
using AgenticAITutor.Repositories;
using Hangfire;
using System.Security.Cryptography;

namespace AgenticAITutor.Services
{
    public class DocumentService : IDocumentService
    {
        private readonly IDocumentRepository documentRepository;
        private readonly IFileStorageService fileStorageService;
        private readonly ISubjectRepository subjectRepository;
        private readonly IConfiguration configuration;
        private readonly IDocumentChunkRepository chunkRepository;
        private readonly HttpClient httpClient;
        private readonly string[] allowedExtensions = { ".pdf", ".docx", ".txt", ".pptx" };
        private readonly long maxFileSize = 10 * 1024 * 1024; // 10 MB

        public DocumentService(IDocumentRepository documentRepository, 
            IFileStorageService fileStorageService, 
            ISubjectRepository subjectRepository, 
            IConfiguration configuration,
            IDocumentChunkRepository chunkRepository,
            IHttpClientFactory httpClientFactory)
        {
            this.documentRepository = documentRepository;
            this.fileStorageService = fileStorageService;
            this.subjectRepository = subjectRepository;
            this.configuration = configuration;
            this.chunkRepository = chunkRepository;
            this.httpClient = httpClientFactory.CreateClient(nameof(DocumentService));
        }

        public async Task<ServiceResponse<DocumentResponse>> UploadDocumentAsync(DocumentRequest request)
        {
            var response = new ServiceResponse<DocumentResponse>();

            // Validate File Existance
            if(request.File == null || request.File.Length == 0)
            {
                response.Success = false;
                response.Message = "File is Empty.";
                return response;
            }

            // Validate File Extension
            var extension = Path.GetExtension(request.File.FileName).ToLower();
            if(!allowedExtensions.Contains(extension))
            {
                response.Success = false;
                response.Message = $"Invalid File Type. Only ({string.Join(", ", allowedExtensions)}) Allowed";
                return response;    
            }

            // Validate File Size
            if(request.File.Length > maxFileSize)
            {
                response.Success = false;
                response.Message = $"File Size Exceeds The {maxFileSize/(1024*1024)} MB Limit";
                return response;
            }

            // Validate File Hash (In Case Of Uploading The Same File)
            string contentHash;
            using (var sha256 = SHA256.Create())
            {
                using (var stream = request.File.OpenReadStream())
                {
                    var hashBytes = await sha256.ComputeHashAsync(stream);
                    contentHash = BitConverter.ToString(hashBytes).Replace("-", "").ToLower();
                }
            }
            var existingDoc = await documentRepository.GetByHashAsync(contentHash, request.UserId);
            if(existingDoc != null)
            {
                response.Success = false;
                response.Message = "You Have Already Uploaded This File. ";
                return response;
            }

            if(request.SubjectId != null && request.SubjectId != Guid.Empty)
            {
                var targetSubject = await subjectRepository.GetByIdAsync(request.SubjectId);
                if (targetSubject == null || targetSubject.UserId != request.UserId)
                {
                    response.Success = false;
                    response.Message = "Target Subject Not Found. ";
                    return response;
                }
            }

            //Storing The File
            string? subFolder = request.SubjectId != Guid.Empty ? request.SubjectId.ToString() : "General";
            string? userFolder = request.UserId.ToString();
            string? storagePath = await fileStorageService.SaveFileAsync(request.File, userFolder, subFolder);

            //Storing The Database Entry
            Document document = new Document
            {
                UserId = request.UserId,
                SubjectId = request.SubjectId,
                Filename = Path.GetFileNameWithoutExtension(request.File.FileName),
                FileSize = (int)request.File.Length,
                FileType = extension, // Here is The File Extension
                StoragePath = storagePath,
                ContentHash = contentHash,
                UploadTime = DateTime.Now,
                ProcessingStatus = DocumentProcessingStatus.PENDING.ToString(),
                KgStatus = KGChunkingStatus.PENDING.ToString(),
            };

            await documentRepository.AddAsync(document);

            // chunking the document
            var jobId = BackgroundJob.Enqueue<DocumentChunkingJob>(job => job.ChunkDocument(document.Id));

            // kg chunking (will only run if the normal chunking job succeeds)
            BackgroundJob.ContinueJobWith<DocumentChunkingJob>(jobId, job => job.KGChunkDocument(document.Id));
                        
            response.Success = true;
            response.Data = MapToResponse(document);
            response.Message = "Upload Successful";

            return response;
        }
        public async Task<ServiceResponse<DocumentResponse>> UpdateDocumentAsync(DocumentUpdate request)
        {
            var response = new ServiceResponse<DocumentResponse>();

            var document = await documentRepository.GetByIdAsync(request.Id);
            
            if(document == null)
            {
                response.Success = false;
                response.Message = "Document Not Found";
                return response;
            }

            if(document.UserId != request.UserId)
            {
                response.Success = false;
                response.Message = "Unauthorized. ";
                return response;
            }

            bool isUpdated = false;

            if(!string.IsNullOrWhiteSpace(request.NewName) && request.NewName != document.Filename)
            {
                document.Filename = request.NewName;
                isUpdated = true;
            }
            //if(request.MoveToGeneral)
            //{
            //    string? userFolder = request.UserId.ToString();
            //    string? newSubFolder = "General";

            //    string? newStoragePath = await fileStorageService.MoveFileAsync(document.StoragePath, userFolder, newSubFolder);
            //    if (newStoragePath != null)
            //        document.StoragePath = newStoragePath;

            //    document.SubjectId = null;
            //    isUpdated = true;
            //}
            else if(request.NewSubjectId != Guid.Empty)
            {
                if(document.SubjectId != request.NewSubjectId)
                {
                    var targetSubject = await subjectRepository.GetByIdAsync(request.NewSubjectId);
                    if(targetSubject == null || targetSubject.UserId != request.UserId)
                    {
                        response.Success = false;
                        response.Message = "Target Subject Not Found. ";
                        return response;
                    }

                    string? userFolder = request.UserId.ToString();
                    string? newSubFolder = request.NewSubjectId.ToString();

                    string? newStoragePath = await fileStorageService.MoveFileAsync(document.StoragePath, userFolder, newSubFolder);
                    if(newStoragePath != null)
                        document.StoragePath = newStoragePath;

                    document.SubjectId = request.NewSubjectId;
                    isUpdated = true;
                }
            }

            if (isUpdated)
            {
                await documentRepository.UpdateAsync(document);
                response.Success = true;
                response.Message = "Document Updated Successfully. ";
            }
            else
                response.Message = "No Changes Were Made. ";

            response.Data = MapToResponse(document);

            return response;
        }

        public async Task<ServiceResponse<string>> DeleteDocumentAsync(Guid documentId, Guid userId)
        {
            var response = new ServiceResponse<string>();

            var document = await documentRepository.GetByIdAsync(documentId);
            if (document == null)
            {
                response.Success = false;
                response.Message = "Document Not Found";
                return response;
            }
            if (document.UserId != userId)
            {
                response.Success = false;
                response.Message = "Unauthorized. ";
                return response;
            }

            // 1. Notify the AI service to delete the knowledge graph data for this document
            try
            {
                var aiBaseUrl = configuration["AIService:BaseURL"];
                var kgDeletePath = configuration["AIService:KGDeletePath"];
                var kgDeleteUrl = $"{aiBaseUrl}/{kgDeletePath}/{documentId}?user_id={userId}";
                await httpClient.DeleteAsync(kgDeleteUrl);
            }
            catch
            {
                // Log and continue — KG cleanup failure should not block the hard delete
            }

            // 2. Delete the physical file from wwwroot/uploads
            if (!string.IsNullOrWhiteSpace(document.StoragePath))
            {
                await fileStorageService.DeleteFileAsync(document.StoragePath);
            }

            // 3. Hard-delete the database record
            await documentRepository.DeleteAsync(document);

            response.Data = "Deleted";
            response.Message = "Document permanently deleted.";
            return response;
        }

        public async Task<List<DocumentResponse>> GetAllDocumentsAsync(Guid userId)
        {
            var documents = await documentRepository.GetAllAsync(userId);
            return documents.Select(MapToResponse).ToList();
        }

        public async Task<List<DocumentResponse>> GetDocumentsBySubjectAsync(Guid userId, Guid subjectId)
        {
            var documents = await documentRepository.GetBySubjectAsync(userId, subjectId);
            return documents.Select(MapToResponse).ToList();
        }

        public async Task<DocumentResponse?> GetDocumentsByIdAsync(Guid userId, Guid id)
        {
            var document = await documentRepository.GetByIdAsync(id);
            if (document is null || document.UserId != userId)
                return null;
            return MapToResponse(document);
        }


        public async Task<ServiceResponse<DocumentResponse>> RetryDocumentProcessingAsync(Guid documentId, Guid userId)
        {
            var response = new ServiceResponse<DocumentResponse>();

            // 1. Find the document and verify ownership
            var document = await documentRepository.GetByIdAsync(documentId);

            if (document == null)
            {
                response.Success = false;
                response.Message = "Document Not Found.";
                return response;
            }

            if (document.UserId != userId)
            {
                response.Success = false;
                response.Message = "Unauthorized.";
                return response;
            }

            // 2. Only allow retry when the previous attempt actually failed.
            //    Prevent re-queuing a document that is already queued or processing.
            if (document.ProcessingStatus != DocumentProcessingStatus.FAILED.ToString())
            {
                response.Success = false;
                response.Message = document.ProcessingStatus switch
                {
                    "PENDING" => "Document is already queued for processing.",
                    "PROCESSING" => "Document is currently being processed. Please wait.",
                    "COMPLETED" => "Document has already been processed successfully.",
                    _ => $"Retry is not allowed for status '{document.ProcessingStatus}'."
                };
                if(document.KgStatus == KGChunkingStatus.FAILED.ToString())
                {
                    BackgroundJob.Enqueue<DocumentChunkingJob>(job => job.KGChunkDocument(document.Id));
                    response.Message += " However, KGChunking has been processing.";
                }
                return response;
            }

            // 3. Clean up any partial chunks that may have been saved before the failure
            await chunkRepository.DeleteByDocumentAsync(documentId);

            // 4. Reset status back to PENDING so the UI reflects the queued state immediately
            document.ProcessingStatus = DocumentProcessingStatus.PENDING.ToString();
            await documentRepository.UpdateAsync(document);

            // 5. Re-enqueue the background chunking job
            var jobId = BackgroundJob.Enqueue<DocumentChunkingJob>(job => job.ChunkDocument(document.Id));

            // 6. Re-enqueue the kg chunking as a continuation
            BackgroundJob.ContinueJobWith<DocumentChunkingJob>(jobId, job => job.KGChunkDocument(document.Id));

            response.Success = true;
            response.Message = "Document has been re-queued for processing.";
            response.Data = MapToResponse(document);
            return response;
        }


        private DocumentResponse MapToResponse(Document document)
        {
            return new DocumentResponse
            {
                Id = document.Id,
                UserId = document.UserId,
                SubjectId = document.SubjectId,
                FileName = document.Filename,
                FileSize = document.FileSize ?? 0,
                FileType = document.FileType,
                UploadTime = document.UploadTime ?? DateTime.Now,
                ProcessingStatus = document.ProcessingStatus,
                KGStatus = document.KgStatus,
                StoragePath = document.StoragePath
            };
        }

    }
}
