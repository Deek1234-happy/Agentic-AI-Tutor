/**
 * Subject service — calls the /api/Subject endpoints defined in swagger.json.
 * All endpoints require a Bearer token.
 *
 *  POST   /api/Subject          → SubjectResponse
 *  GET    /api/Subject          → SubjectResponse[]
 *  GET    /api/Subject/{id}     → SubjectResponse
 *  PUT    /api/Subject/{id}     → string
 *  DELETE /api/Subject/{id}     → string
 */

import { apiClient } from "../lib/apiClient";
import type { SubjectRequest, SubjectResponse } from "../types/subject";

/** Fetch all subjects owned by the authenticated user */
export async function getSubjects(): Promise<SubjectResponse[]> {
  return apiClient.get<SubjectResponse[]>("/api/Subject", { auth: true });
}

/** Fetch a single subject (includes its documents) */
export async function getSubjectById(id: string): Promise<SubjectResponse> {
  return apiClient.get<SubjectResponse>(`/api/Subject/${id}`, { auth: true });
}

/** Create a new subject */
export async function createSubject(payload: SubjectRequest): Promise<SubjectResponse> {
  return apiClient.post<SubjectResponse>("/api/Subject", payload, { auth: true });
}

/** Rename a subject */
export async function updateSubject(id: string, payload: SubjectRequest): Promise<string> {
  return apiClient.put<string>(`/api/Subject/${id}`, payload, { auth: true });
}

/** Delete a subject (also deletes all its documents and KG data) */
export async function deleteSubject(id: string): Promise<string> {
  return apiClient.delete<string>(`/api/Subject/${id}`, { auth: true });
}
