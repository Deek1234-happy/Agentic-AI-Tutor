/**
 * Document service — calls the /api/Document endpoints defined in swagger.json.
 * All endpoints require a Bearer token.
 *
 *  POST   /api/Document                          → DocumentResponse  (multipart/form-data)
 *  GET    /api/Document                          → DocumentResponse[]
 *  GET    /api/Document/{id}                     → DocumentResponse
 *  DELETE /api/Document/{id}                     → string
 *  GET    /api/Document/subject/{subjectId}       → DocumentResponse[]
 *  POST   /api/Document/{id}/retry-processing    → DocumentResponse
 *  GET    /api/Document/{id}/download            → file stream (blob)
 */

import { getToken } from "../lib/apiClient";
import type { DocumentResponse, DocumentUploadPayload } from "../types/subject";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5099";

// ─── Helper: authenticated fetch for non-JSON responses ───────────────────────

export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers as HeadersInit | undefined);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401) {
    // Delegate to global 401 handler pattern
    throw new Error("Session expired. Please log in again.");
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response;
}

// ─── Upload (multipart/form-data) ─────────────────────────────────────────────

/**
 * Upload a document.
 * SubjectId is MANDATORY — no document may exist without a subject.
 * The payload is sent as multipart/form-data (not JSON) because it includes a binary File.
 */
export async function uploadDocument(payload: DocumentUploadPayload): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("UserId", payload.userId);
  formData.append("SubjectId", payload.subjectId);
  formData.append("File", payload.file);

  const response = await authFetch("/api/Document", {
    method: "POST",
    body: formData,
    // NOTE: do NOT set Content-Type — the browser sets it with the correct boundary
  });

  return response.json() as Promise<DocumentResponse>;
}

// ─── Read ─────────────────────────────────────────────────────────────────────

/** Get all documents for the authenticated user */
export async function getAllDocuments(): Promise<DocumentResponse[]> {
  const response = await authFetch("/api/Document");
  return response.json() as Promise<DocumentResponse[]>;
}

/** Get a single document by ID */
export async function getDocumentById(id: string): Promise<DocumentResponse> {
  const response = await authFetch(`/api/Document/${id}`);
  return response.json() as Promise<DocumentResponse>;
}

/**
 * Get all documents belonging to a specific subject.
 * Use this on the Subject Detail page — enforces the Subject → Document hierarchy.
 */
export async function getDocumentsBySubject(subjectId: string): Promise<DocumentResponse[]> {
  const response = await authFetch(`/api/Document/subject/${subjectId}`);
  return response.json() as Promise<DocumentResponse[]>;
}

// ─── Delete ───────────────────────────────────────────────────────────────────

/** Permanently delete a document (also purges KG data) */
export async function deleteDocument(id: string): Promise<string> {
  const response = await authFetch(`/api/Document/${id}`, { method: "DELETE" });
  return response.text();
}

// ─── Retry processing ─────────────────────────────────────────────────────────

/** Retry a FAILED document's processing pipeline */
export async function retryDocumentProcessing(id: string): Promise<DocumentResponse> {
  const response = await authFetch(`/api/Document/${id}/retry-processing`, { method: "POST" });
  return response.json() as Promise<DocumentResponse>;
}

// ─── Download / View ─────────────────────────────────────────────────────────
// Both use GET /api/Document/{id}/download (requires Bearer token).
// Since the endpoint streams raw bytes, we fetch as a blob and create a
// temporary object URL instead of redirecting (which would bypass the auth header).

/**
 * Trigger the browser's Save-As dialog for a document.
 */
export async function downloadDocument(id: string, fileName: string): Promise<void> {
  const response = await authFetch(`/api/Document/${id}/download`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  // Revoke after a short delay so the browser has time to start the download
  setTimeout(() => URL.revokeObjectURL(url), 5_000);
}

/**
 * Get a blob URL for a document to view it inline.
 * The caller is responsible for revoking the URL when done.
 */
export async function getDocumentViewUrl(id: string): Promise<string> {
  const response = await authFetch(`/api/Document/${id}/download`);
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
