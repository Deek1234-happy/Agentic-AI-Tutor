using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
namespace AgenticAITutor.Services
{
    public class LocalFileStorageService : IFileStorageService
    {
        private readonly IWebHostEnvironment webHostEnvironment;

        public LocalFileStorageService(IWebHostEnvironment webHostEnvironment)
        {
            this.webHostEnvironment = webHostEnvironment;
        }

        public async Task<string> SaveFileAsync(IFormFile file, string userFolder, string subFolder)
        {
            string webRootPath = webHostEnvironment.WebRootPath;
            if (string.IsNullOrEmpty(webRootPath))
                webRootPath = Path.Combine(webHostEnvironment.ContentRootPath, "wwwroot");

            var uploadsFolder = Path.Combine(webRootPath, "uploads", userFolder ,subFolder);
            if (!Directory.Exists(uploadsFolder))
                Directory.CreateDirectory(uploadsFolder);

            var uniqueFileName = Guid.NewGuid().ToString() + Path.GetExtension(file.FileName);
            var filePath = Path.Combine(uploadsFolder, uniqueFileName);

            using (var fileStream = new FileStream(filePath, FileMode.Create))
            {
                await file.CopyToAsync(fileStream);
            }

            return Path.Combine("uploads", userFolder ,subFolder, uniqueFileName).Replace("\\", "/");
            
        }

        public async Task<string> SaveFileAsync(byte[] fileBytes, string fileName, string userFolder, string subFolder)
        {
            string webRootPath = webHostEnvironment.WebRootPath;
            if (string.IsNullOrEmpty(webRootPath))
                webRootPath = Path.Combine(webHostEnvironment.ContentRootPath, "wwwroot");

            var uploadsFolder = Path.Combine(webRootPath, "uploads", userFolder, subFolder);
            if (!Directory.Exists(uploadsFolder))
                Directory.CreateDirectory(uploadsFolder);

            var uniqueFileName = Guid.NewGuid().ToString() + Path.GetExtension(fileName);
            var filePath = Path.Combine(uploadsFolder, uniqueFileName);

            await File.WriteAllBytesAsync(filePath, fileBytes);

            return Path.Combine("uploads", userFolder, subFolder, uniqueFileName).Replace("\\", "/");
        }


        public Task DeleteFileAsync(string relativePath)
        {
            string webRootPath = webHostEnvironment.WebRootPath;
            if (string.IsNullOrEmpty(webRootPath))
                webRootPath = Path.Combine(webHostEnvironment.ContentRootPath, "wwwroot");

            var filePath = Path.Combine(webRootPath, relativePath);
            return Task.Run(() =>
            {
                if (File.Exists(filePath))
                    File.Delete(filePath);
            });
        }

        public Task<bool> FileExistsAsync(string relativePath)
        {
            string webRootPath = webHostEnvironment.WebRootPath;
            if (string.IsNullOrEmpty(webRootPath))
                webRootPath = Path.Combine(webHostEnvironment.ContentRootPath, "wwwroot");

            var filePath = Path.Combine(webRootPath, relativePath);
            return Task.FromResult(File.Exists(filePath));
        }

        public async Task<string> MoveFileAsync(string oldRelativePath, string userFolder, string newSubFolder)
        {
            string webRootPath = webHostEnvironment.WebRootPath;
            if (string.IsNullOrEmpty(webRootPath))
                webRootPath = Path.Combine(webHostEnvironment.ContentRootPath, "wwwroot");

            string oldFullPath = Path.Combine(webRootPath, oldRelativePath);
            if (!File.Exists(oldFullPath))
                return null;

            string newFolderPath = Path.Combine(webRootPath, "uploads", userFolder, newSubFolder);
            if(!Directory.Exists(newFolderPath))
                Directory.CreateDirectory(newFolderPath);

            string fileName = Path.GetFileName(oldFullPath);
            string newFullPath = Path.Combine(newFolderPath, fileName);

            await Task.Run(() => File.Move(oldFullPath, newFullPath));
            return Path.Combine("uploads", userFolder, newSubFolder, fileName).Replace("\\", "/");

        }
    }
}
