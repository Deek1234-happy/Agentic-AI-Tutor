using AgenticAITutor.Models;
using AgenticAITutor.Models.DTOs;
using AgenticAITutor.Repositories;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace AgenticAITutor.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AIRetrievalController : ControllerBase
    {
        private readonly IDocumentChunkRepository chunkRepository;

        public AIRetrievalController(IDocumentChunkRepository chunkRepository)
        {
            this.chunkRepository = chunkRepository;
        }

        [HttpPost("retrieve")]
        public async Task<IActionResult> Retrieve([FromBody] UserMessageRequest request)
        {
            await Task.Delay(2000);

            List<DocumentChunk> allAllowedChunks = new List<DocumentChunk>();

            if(request.AllowedDocumentIds != null)
            {
                foreach(var docId in request.AllowedDocumentIds)
                {
                    var chunks = await chunkRepository.GetByDocumentAsync(docId, request.UserId);
                    allAllowedChunks.AddRange(chunks);
                }
            }

            var response = new AIMessageResponse
            {
                AIMessage = $"This is a simulated AI response to your question '{request?.UserMessage}'. Based on your documents, The system found relevant information",
                UsedChunks = new List<AICitationDTO>()
            };

           if(allAllowedChunks.Count > 0 )
            {
                int maxChunks = Math.Min(2, allAllowedChunks.Count);
                for (int i = 0; i < maxChunks; i++)
                {
                    int randomIndex = Random.Shared.Next(0, allAllowedChunks.Count);
                    var selectedChunk = allAllowedChunks[randomIndex];

                    response.UsedChunks.Add(new AICitationDTO
                    {
                        ChunkId = selectedChunk.Id,
                        DocumentId = selectedChunk.DocumentId,
                        RelevanceScore = 0.92 - (i * 0.05) // Fake varying scores
                    });

                    allAllowedChunks.RemoveAt(randomIndex); // Prevent picking the same chunk twice
                }
            }

            return Ok(response);
        }
    }
}
