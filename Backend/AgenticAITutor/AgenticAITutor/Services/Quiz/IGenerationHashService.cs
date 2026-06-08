namespace AgenticAITutor.Services
{
    public interface IGenerationHashService
    {
        /// <summary>
        /// Computes a deterministic SHA-256 hash from the userId and a sorted
        /// list of document IDs. Used to detect duplicate quiz generation requests.
        /// </summary>
        string ComputeHash(Guid userId, List<Guid> documentIds, int numberOfQuestions);
    }
}
