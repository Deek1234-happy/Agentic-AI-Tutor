# Web Search Service

A standalone n8n workflow that performs web search using Tavily and generates concise answers using an LLM through OpenRouter.

This workflow was originally developed as a component of the Agentic AI Tutor system and extracted into a separate branch for independent development, testing, and deployment.

## Features

- Web search using Tavily Search API
- AI-powered answer generation using OpenRouter
- Automatic language matching with the user's query
- Returns both generated answers and source links
- Simple webhook-based API integration

## Workflow Architecture

1. **Webhook Trigger**
   - Receives the user's search query.

2. **Web Search**
   - Sends the query to Tavily Search API.
   - Retrieves the top 3 relevant results.

3. **Result Formatting**
   - Organizes search results for downstream processing.
   - Preserves the original user question.

4. **Answer Generation**
   - Sends the retrieved content to OpenRouter.
   - Generates a concise and coherent response.
   - Ensures the response language matches the user's language.

5. **Response Delivery**
   - Returns the generated answer.
   - Includes source titles, URLs, and domains.

## Environment Variables

```env
TAVILY_API_KEY=your_tavily_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## API Endpoint

### Request

```http
POST /web-search
```

### Request Body

```json
{
  "query": "What is Retrieval-Augmented Generation?",
  "original_question": "What is Retrieval-Augmented Generation?"
}
```

### Response

```json
{
  "answer": "Retrieval-Augmented Generation (RAG) combines information retrieval with large language models to provide responses grounded in external knowledge.",
  "sources": [
    {
      "title": "Introduction to RAG",
      "url": "https://example.com",
      "domain": "example.com"
    }
  ]
}
```

## Notes

- Tavily is used exclusively for information retrieval.
- OpenRouter is used to summarize and generate the final answer.
- Source URLs are returned separately from the generated response.
- The workflow automatically adapts the answer language to match the user's question.
- This workflow is part of the Agentic AI Tutor ecosystem but can be deployed independently as a reusable web-search microservice.
