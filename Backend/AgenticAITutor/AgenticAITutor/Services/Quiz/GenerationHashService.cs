using System.Security.Cryptography;
using System.Text;

namespace AgenticAITutor.Services
{
    public class GenerationHashService : IGenerationHashService
    {
        /// <summary>
        /// Hash = SHA256( userId + ":" + sorted_documentIds.Join(",") )
        /// Sorting ensures that [doc1, doc2] and [doc2, doc1] produce the same hash.
        /// </summary>
        public string ComputeHash(Guid userId, List<Guid> documentIds)
        {
            // Lexicographic sort on the string representation of each GUID
            var sortedIds = documentIds
                .Select(id => id.ToString())
                .OrderBy(id => id, StringComparer.Ordinal)
                .ToList();

            var raw = $"{userId}:{string.Join(",", sortedIds)}";

            using var sha256 = SHA256.Create();
            var hashBytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(raw));
            return BitConverter.ToString(hashBytes).Replace("-", "").ToLower();
        }
    }
}
