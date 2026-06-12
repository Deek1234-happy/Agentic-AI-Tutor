# GenT AI Tutor — Frontend UI

A React frontend for an intelligent learning platform where students can organize subjects, upload study materials, chat with an AI tutor, take AI-generated quizzes, review knowledge graph context, and track learning progress through dynamic analytics dashboards.

This project was originally generated from a Figma design and has been adapted into a Vite-based frontend that connects to a .NET backend API.

## Features

- **Authentication** — Register, login, protected dashboard routes, persisted JWT sessions, and a full 2-step Forgot / Reset / Change Password flow
- **Subject Management** — Organize learning spaces by subject with dedicated material libraries
- **Document Management** — Upload, download, view, delete, and retry processing of study materials
- **AI Tutor Chat** — Chat sessions with message history, AI citations, knowledge graph context, and optional web search augmentation
- **Quiz Engine** — Generate quizzes from uploaded documents, take exams through a focused single-question UI, and review completed attempts with per-question AI-generated explanations
- **Progress & Analytics** — Dynamic visualizations of study consistency, subject mastery levels, and AI-identified weak concepts powered by Recharts
- **Knowledge Graph** — Visual exploration of concepts and their relationships extracted from study materials
- **Profile Management** — Edit profile details, update avatar, and manage account preferences
- **Speech Integration** — Speech-to-text and text-to-speech integration points for accessible interaction
- **Theming** — Light/dark theme support with a responsive sidebar navigation layout

## Tech Stack

| Category            | Library / Tool              |
| ------------------- | --------------------------- |
| Framework           | React 18                    |
| Language            | TypeScript                  |
| Build Tool          | Vite                        |
| Routing             | React Router v6             |
| Server State        | TanStack Query (React Query)|
| Styling             | Tailwind CSS                |
| Component Primitives| Radix UI                    |
| Charts              | Recharts                    |
| Icons               | Lucide React, Material UI Icons |

## Prerequisites

- Node.js 18 or newer
- npm
- A running instance of the GenT AI Tutor .NET backend API

## Getting Started

**1. Install dependencies:**

```bash
npm install
```

**2. Create a local environment file:**

```bash
cp .env.example .env
```

**3. Update `.env` if your backend is not running on the default URL:**

```env
VITE_API_BASE_URL=http://localhost:5099
```

**4. Start the development server:**

```bash
npm run dev
```

Vite will print the local URL in the terminal, usually `http://localhost:5173`.

## Available Scripts

```bash
npm run dev
```
Starts the Vite development server with hot module replacement.

```bash
npm run build
```
Creates an optimized production build in `dist/`.

```bash
npm run preview
```
Serves the production build locally for pre-deployment verification.

## Project Structure

```text
src/
  app/
    components/     Reusable UI, layout, chat, quiz, and subject components
    layouts/        Main authenticated app layout with sidebar
    pages/          Route pages: Dashboard, Subjects, Chat, Quiz, Progress, Settings, Auth
    routes.ts       Application route definitions
  context/          Auth context and session state management
  hooks/            React Query hooks for subjects, documents, chat, quiz, analytics, and profile
  lib/              Shared API client, session helpers, and utility functions
  services/         Backend API service wrappers (one per controller group)
  styles/           Global CSS, theme tokens, Tailwind config, and font styles
  types/            Shared TypeScript interfaces and type definitions
```

## Routes

### Public Routes

| Route              | Description                                      |
| ------------------ | ------------------------------------------------ |
| `/`                | Welcome, login, and registration entry point     |
| `/forgot-password` | Step 1 of password reset — request reset email   |
| `/reset-password`  | Step 2 of password reset — submit new password via token |

### Protected Routes (require authentication)

| Route                                          | Description                                          |
| ---------------------------------------------- | ---------------------------------------------------- |
| `/dashboard`                                   | Main overview dashboard                              |
| `/dashboard/subjects`                          | Subject list and management                          |
| `/dashboard/subjects/:subjectId`               | Subject detail view with documents                  |
| `/dashboard/chat`                              | AI tutor chat interface                              |
| `/dashboard/quizzes`                           | Quiz generation, history, and management             |
| `/dashboard/quizzes/:quizId/take`              | Active exam interface (single-question, timed UI)    |
| `/dashboard/quizzes/attempts/:attemptId/review`| Exam results with per-question AI explanations       |
| `/dashboard/progress`                          | Progress and analytics dashboard                     |
| `/dashboard/settings`                          | User settings and profile management                 |
| `/dashboard/notifications`                     | Notification center                                  |

All `/dashboard/*` routes are guarded by an authentication check. Unauthenticated users are redirected to `/`.

## Backend Configuration

The frontend reads the backend base URL from `VITE_API_BASE_URL`. All service modules prepend this value to their request paths.

The current service layer expects the following API controller groups to be available on the backend:

| API Group          | Purpose                                              |
| ------------------ | ---------------------------------------------------- |
| `/api/Auth`        | Login, register, password reset flow                 |
| `/api/User`        | Profile retrieval and update                         |
| `/api/Subject`     | Subject CRUD operations                              |
| `/api/Document`    | Document upload, management, and processing status   |
| `/api/ChatSession` | Chat session lifecycle management                    |
| `/api/ChatMessage` | Message history and AI response streaming            |
| `/api/Quiz`        | Quiz generation, attempt submission, and review      |
| `/api/Analytics`   | Progress tracking, mastery scores, and weak concepts |

Authenticated requests automatically attach the stored JWT as a `Bearer` token via an Axios request interceptor.

## Environment Variables

| Variable            | Description                                                        | Default                  |
| ------------------- | ------------------------------------------------------------------ | ------------------------ |
| `VITE_API_BASE_URL` | Base URL for the .NET backend API, **without** a trailing slash    | `http://localhost:5099`  |

## Notes

- Do not commit `.env`; use `.env.example` as the shared template for environment variable keys.
- `dist/` and `node_modules/` are intentionally excluded from version control via `.gitignore`.
- The original Figma design reference is included for attribution: [AI-Powered Learning Platform (Figma)](https://www.figma.com/design/T53cYt8vkzlX5cZDQtusQe/AI-Powered-Learning-Platform)
