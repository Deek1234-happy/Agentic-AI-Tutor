/**
 * Subject & Document DTOs — generated from swagger.json (source of truth)
 *
 * Endpoints covered:
 *   Subject:  POST/GET /api/Subject  |  GET/PUT/DELETE /api/Subject/{id}
 *   Document: POST/GET /api/Document  |  GET/DELETE /api/Document/{id}
 *             GET /api/Document/subject/{subjectId}
 */

// ─── Subject ──────────────────────────────────────────────────────────────────

/** POST /api/Subject — request body */
export interface SubjectRequest {
  name: string;                   // required, maxLength 255
}

/** GET /api/Subject / GET /api/Subject/{id} — response */
export interface SubjectResponse {
  id: string;                     // uuid
  name: string | null;
  userId: string;                 // uuid
  documents: DocumentResponse[] | null;
}

// ─── Document ─────────────────────────────────────────────────────────────────

/**
 * DocumentResponse — returned by most Document endpoints.
 * `processingStatus` values observed from the backend: PENDING | PROCESSING | COMPLETED | FAILED
 */
export interface DocumentResponse {
  id: string;                     // uuid
  subjectId: string;              // uuid — always present; docs MUST belong to a subject
  userId: string;                 // uuid
  fileName: string | null;
  fileType: string | null;
  fileSize: number | null;        // bytes
  uploadTime: string | null;      // date-time
  processingStatus: string | null;
  kgStatus: string | null;
  storagePath: string | null;
}

/**
 * Lightweight DTO used for dropdowns.
 * GET /api/Subject/{id}/documents/dropdown
 */
export interface DocumentDropdownResponse {
  id: string;                     // uuid
  fileName: string | null;
}

/** PUT /api/Document — request body */
export interface DocumentUpdate {
  id: string;                     // uuid, required
  userId: string;                 // uuid, required
  newName?: string | null;
  newSubjectId?: string;          // uuid
}

/**
 * POST /api/Document — multipart/form-data fields.
 * NOTE: the API contract requires UserId, File, and SubjectId.
 * SubjectId is MANDATORY — documents cannot exist without a subject.
 */
export interface DocumentUploadPayload {
  userId: string;                 // uuid (from session)
  file: File;
  subjectId: string;              // uuid (required — no unassigned state)
}
