using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Services
{
    public interface IFileStorageService
    {
        Task<string> SaveFileAsync(IFormFile file,string userFolder, string subFolder);
        Task DeleteFileAsync(string relativePath);
        Task<string> MoveFileAsync(string oldRelativePath, string userFolder, string newSubFolder);
    }
}
