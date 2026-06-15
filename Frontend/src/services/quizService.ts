import { apiClient } from "../lib/apiClient";
import type {
  QuizAttemptSummary,
  QuizHistoryItem,
  QuizHistoryQuery,
  QuizInitiateRequest,
  QuizInitiateResponse,
  QuizReviewResponse,
  QuizStartResponse,
  QuizStatusResponse,
  QuizSubmitRequest,
  QuizSubmitResponse,
} from "../types/quiz";

function toQueryString(query?: QuizHistoryQuery): string {
  if (!query) return "";

  const params = new URLSearchParams();
  if (query.subjectId) params.set("SubjectId", query.subjectId);
  if (query.status) params.set("Status", query.status);
  if (query.page) params.set("Page", query.page.toString());
  if (query.pageSize) params.set("PageSize", query.pageSize.toString());

  const value = params.toString();
  return value ? `?${value}` : "";
}

export function initiateQuiz(payload: QuizInitiateRequest): Promise<QuizInitiateResponse> {
  return apiClient.post<QuizInitiateResponse>("/api/Quiz/initiate", payload, { auth: true });
}

export function checkStatus(quizId: string): Promise<QuizStatusResponse> {
  return apiClient.get<QuizStatusResponse>(`/api/Quiz/${quizId}/status`, { auth: true });
}

export function startAttempt(quizId: string): Promise<QuizStartResponse> {
  return apiClient.get<QuizStartResponse>(`/api/Quiz/${quizId}/start`, { auth: true });
}

export function submitQuiz(quizId: string, payload: QuizSubmitRequest): Promise<QuizSubmitResponse> {
  return apiClient.post<QuizSubmitResponse>(`/api/Quiz/${quizId}/submit`, payload, { auth: true });
}

export function getQuizHistory(query?: QuizHistoryQuery): Promise<QuizHistoryItem[]> {
  return apiClient.get<QuizHistoryItem[]>(`/api/Quiz/history${toQueryString(query)}`, { auth: true });
}

export async function getQuizById(quizId: string): Promise<QuizHistoryItem | null> {
  const quizzes = await getQuizHistory({ page: 1, pageSize: 100 });
  return quizzes.find((quiz) => quiz.quizId === quizId) ?? null;
}

export function getQuizAttempts(quizId: string): Promise<QuizAttemptSummary[]> {
  return apiClient.get<QuizAttemptSummary[]>(`/api/Quiz/${quizId}/attempts`, { auth: true });
}

export function reviewAttempt(attemptId: string): Promise<QuizReviewResponse> {
  return apiClient.get<QuizReviewResponse>(`/api/Quiz/attempt/${attemptId}/review`, { auth: true });
}
