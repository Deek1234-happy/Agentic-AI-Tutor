# Agentic-AI-Tutor
Agentic AI Tutor is a personalized learning platform that uses agentic AI and retrieval-augmented generation to provide citation-based explanations, adaptive quizzes, and guided study support using only student-uploaded materials.
## 🛠 Prerequisites

Before you start, ensure you have the following installed on your machine:
* **[.NET SDK 8.0](https://dotnet.microsoft.com/download/dotnet/8.0)**
* **Git**
* **Visual Studio 2022** OR **Visual Studio Code** (with the C# Dev Kit extension)

*Note: You do not need to install PostgreSQL locally unless you want an isolated database. We have a shared cloud database configured in the project.*

## ⚙️ Local Setup Instructions

### 1. Clone the Repository
Open your terminal and clone the project:
```bash
git clone https://github.com/Rehab-Hamdy/Agentic-AI-Tutor/tree/backend
cd AgenticAITutor

2. Configure Your Local Environment (appsettings.Development.json)
We use appsettings.Development.json for local testing so we don't accidentally push local URLs to production.

Create a file named appsettings.Development.json in the same folder as appsettings.json (if it isn't there already), and add this configuration. Make sure to change the AIService URLs to point to your running Python FastAPI server (e.g., http://127.0.0.1:8000).

JSON
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com;Port=18990;Database=AgenticAITutor;Username=avnadmin;Password=ASK_REEM_FOR_PASSWORD;Ssl Mode=Require;Trust Server Certificate=true"
  },
  "AppConfig": {
    "BaseURL": "http://localhost:5000" 
  },
  "AIService": {
    "BaseURL": "[http://127.0.0.1:8000](http://127.0.0.1:8000)", 
    "ChunkingPath": "extract/embed",
    "ChatPath": "chat/"
  }
}
(Reach out to the backend team for the actual Database Password and JWT Key to put in your local config).

3. Run the Project
To start the C# backend, open your terminal in the project folder and run:

Bash
dotnet run
The API will start (usually on http://localhost:5000 or https://localhost:5001).
To view the API documentation and test endpoints, open your browser and go to:
👉 http://localhost:5000/swagger