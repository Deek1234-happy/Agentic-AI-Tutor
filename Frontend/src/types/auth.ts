/**
 * Auth DTOs — generated from swagger.json (source of truth)
 * Endpoints: POST /api/Auth/register | POST /api/Auth/login
 */

/** POST /api/Auth/register — request body */
export interface RegisterRequest {
  firstName: string | null;
  lastName: string | null;
  email: string | null;
  password: string | null;
}

/** POST /api/Auth/login — request body */
export interface LoginRequest {
  email: string | null;
  password: string | null;
}

export interface ForgotPasswordRequest {
  email: string | null;
}

export interface ResetPasswordRequest {
  email: string | null;
  otp: string | null;
  newPassword: string | null;
  confirmNewPassword: string | null;
}

export interface ChangePasswordRequest {
  oldPassword: string | null;
  newPassword: string | null;
  confirmNewPassword: string | null;
}

/** Shared success response for both register and login (200) */
export interface AuthResponse {
  userId: string;           // uuid
  email: string | null;
  token: string | null;
  expiresIn: string;        // date-time
  message: string | null;
  isAuthenticated: boolean;
}

/** Stored in localStorage / auth context after a successful auth call */
export interface StoredSession {
  userId: string;
  email: string;
  token: string;
  expiresIn: string;
}
