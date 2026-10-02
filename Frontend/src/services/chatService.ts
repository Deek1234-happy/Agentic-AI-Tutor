import { apiClient } from "../lib/apiClient";
import { authFetch } from "./documentService"; // Reusing the wrapper that sets Authorization headers
import type {
  ChatSessionRequest,
  ChatSessionResponse,
  ChatSessionUpdate,
  UserMessageRequest,
  AIMessageResponse,
  WebSearchResponse,
  ChatMessageResponse,
  STTResponse,
  TTSResponse,
} from "../types/chat";

// ─── Sessions ──────────────────────────────────────────────────────────────────

export async function createChatSession(payload: ChatSessionRequest): Promise<ChatSessionResponse> {
  return apiClient.post<ChatSessionResponse>("/api/ChatSession", payload, { auth: true });
}

export async function getChatSessions(): Promise<ChatSessionResponse[]> {
  return apiClient.get<ChatSessionResponse[]>("/api/ChatSession", { auth: true });
}

export async function updateChatSessionTitle(payload: ChatSessionUpdate): Promise<void> {
  return apiClient.put<void>("/api/ChatSession", payload, { auth: true });
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  return apiClient.delete<void>(`/api/ChatSession/${sessionId}`, { auth: true });
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export async function getChatMessages(sessionId: string): Promise<ChatMessageResponse[]> {
  return apiClient.get<ChatMessageResponse[]>(`/api/ChatMessage/${sessionId}`, { auth: true });
}

export async function sendChatMessage(payload: UserMessageRequest): Promise<AIMessageResponse> {
  const body = {
    SessionId: payload.sessionId,
    session_id: payload.sessionId,
    UserMessage: payload.userMessage,
    userMessage: payload.userMessage,
    question: payload.userMessage,
    SearchWeb: false,
    searchWeb: false,
  };
  return apiClient.post<AIMessageResponse>("/api/ChatMessage/SendMessage", body, { auth: true });
}

export async function searchWebMessage(payload: UserMessageRequest): Promise<WebSearchResponse> {
  const body = {
    SessionId: payload.sessionId,
    session_id: payload.sessionId,
    UserMessage: payload.userMessage,
    userMessage: payload.userMessage,
    question: payload.userMessage,
    SearchWeb: true,
    searchWeb: true,
  };
  return apiClient.post<WebSearchResponse>("/api/ChatMessage/SearchWeb", body, { auth: true });
}

// ─── Audio (STT / TTS) ────────────────────────────────────────────────────────

/**
 * Upload an audio file to transcribe to text.
 * Requires multipart/form-data.
 */
export async function transcribeAudio(audioFile: File): Promise<STTResponse> {
  const formData = new FormData();
  formData.append("audio_file", audioFile);

  const response = await authFetch("/api/ChatMessage/STT", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `STT failed with status ${response.status}`);
  }

  return response.json() as Promise<STTResponse>;
}

/**
 * Generate playable TTS audio URL for an existing message.
 */
export async function generateTTS(messageId: string): Promise<TTSResponse> {
  return apiClient.post<TTSResponse>(`/api/ChatMessage/${messageId}/TTS`, {}, {
    auth: true,
    timeoutMs: 180000,
  });
}
