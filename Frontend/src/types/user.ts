/**
 * User DTOs — generated from swagger.json (source of truth)
 * Endpoint: GET /api/User/profile  (Bearer required)
 *           PUT /api/User/profile  (Bearer required)
 */

/** GET /api/User/profile — 200 response */
export interface UserResponse {
  id: string;                      // uuid
  firstName: string | null;
  lastName: string | null;
  email: string | null;
  createdDate: string | null;      // date-time
  numberOfSubjects: number;
  numberOfDocuments: number;
  numberOfQuizzes: number;
}

export type UserProfileResponse = UserResponse;

/** PUT /api/User/profile — request body */
export interface UserUpdateRequest {
  firstName?: string | null;
  lastName?: string | null;
  email?: string | null;           // format: email
}

export type UpdateProfileRequest = UserUpdateRequest;
