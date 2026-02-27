using AgenticAITutor.Models.DTOs;

namespace AgenticAITutor.Services
{
    public interface IDocumentService
    {
        Task<ServiceResponse<DocumentResponse>> UploadDocumentAsync (DocumentRequest request);
        Task<ServiceResponse<DocumentResponse>> UpdateDocumentAsync (DocumentUpdate request);
        Task<ServiceResponse<string>> DeleteDocumentAsync (Guid documentId, Guid userId);
        Task<List<DocumentResponse>> GetAllDocumentsAsync(Guid userId);
        Task<List<DocumentResponse>> GetDocumentsBySubjectAsync(Guid userId, Guid subjectId);
        Task<DocumentResponse?> GetDocumentsByIdAsync(Guid userId, Guid id);
    }
}
