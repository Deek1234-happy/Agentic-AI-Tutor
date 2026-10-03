import type { LanguageCode } from "./language";

export interface ChatSessionRequest {
  documentIds?: string[];
}

export interface ChatSessionResponse {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatSessionUpdate {
  sessionId: string;
  title: string;
}

export interface UserMessageRequest {
  sessionId: string;
  userMessage: string;
  searchWeb: boolean;
  language?: LanguageCode;
}

export interface Citation {
  document_id?: string;
  chunk_id?: string;
  page_start?: number;
  page_end?: number;
  document_name?: string;
  file_name?: string;
  fileName?: string;
  snippet?: string;
  content?: string;
}

export interface KgEntity {
  id: string;
  name: string;
  label: string;
}

export interface KgRelation {
  source: string;
  target: string;
  type?: string;
  label?: string;
  relation?: string;
  weight?: number;
}

export interface KnowledgeGraphContext {
  entities: KgEntity[];
  relationships: KgRelation[];
}

export interface AIMessageResponse {
  messageId: string;
  answer: string;
  confidenceScore: number;
  citations: Citation[];
  kgContext?: KnowledgeGraphContext;
}

export interface WebSearchSource {
  title: string;
  url: string;
  snippet: string;
}

export interface WebSearchResponse {
  messageId: string;
  answer: string;
  sources: WebSearchSource[];
}

export interface ChatMessageResponse {
  id: string;
  sessionId: string;
  role: string;
  content: string;
  createdAt: string;
  // Optional AI metadata attached to the message model by the backend
  aiCitation?: Citation[];
  kgContext?: KnowledgeGraphContext;
  kg_context?: KnowledgeGraphContext;
  webSource?: WebSearchSource[];
  audioUrl?: string;
  confidenceScore?: number;
}

export interface STTResponse {
  text: string;
}

export interface TTSResponse {
  audio_url: string;
}
