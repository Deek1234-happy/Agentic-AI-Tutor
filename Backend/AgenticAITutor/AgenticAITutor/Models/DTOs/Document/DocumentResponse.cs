namespace AgenticAITutor.Models.DTOs
{
    public class DocumentResponse
    {
        public Guid? Id { get; set; }
        public Guid? SubjectId { get; set; }
        public Guid? UserId { get; set; }
        public string FileName { get; set; }
        public string FileType { get; set; }
        public int? FileSize { get; set; }
        public DateTime? UploadTime { get; set; }
        public string ProcessingStatus { get; set; }

        public string StoragePath { get; set; }
    }
}
