/**
 * Auth service — thin layer over apiClient that calls the exact endpoints
 * defined in swagger.json.
 *
 *  POST /api/Auth/register  → AuthResponse
 *  POST /api/Auth/login     → AuthResponse
 *
 * Both endpoints are public (no Bearer token required).
 * On success the JWT is persisted via apiClient helpers so subsequent
 * requests to protected endpoints will pick it up automatically.
 */

import { apiClient, saveToken, saveSession, clearSession } from "../lib/apiClient";
import type {
  RegisterRequest,
  LoginRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  ChangePasswordRequest,
  AuthResponse,
  StoredSession,
} from "../types/auth";

// ─── Register ─────────────────────────────────────────────────────────────────

export async function register(payload: RegisterRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/Auth/register", payload);
  persistSession(response);
  return response;
}

// ─── Login ────────────────────────────────────────────────────────────────────

export async function login(payload: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/Auth/login", payload);
  persistSession(response);
  return response;
}

export async function forgotPassword(payload: ForgotPasswordRequest): Promise<string> {
  return apiClient.post<string>("/api/Auth/forgot-password", payload);
}

export async function resetPassword(payload: ResetPasswordRequest): Promise<string> {
  return apiClient.post<string>("/api/Auth/reset-password", payload);
}

export async function changePassword(payload: ChangePasswordRequest): Promise<string> {
  return apiClient.post<string>("/api/Auth/change-password", payload, { auth: true });
}

// ─── Logout ───────────────────────────────────────────────────────────────────

export function logout(): void {
  clearSession();
}

// ─── Internal ─────────────────────────────────────────────────────────────────

function persistSession(response: AuthResponse): void {
  if (response.token) {
    saveToken(response.token);
  }

  const session: StoredSession = {
    userId: response.userId,
    email: response.email ?? "",
    token: response.token ?? "",
    expiresIn: response.expiresIn,
  };
  saveSession(session);
}
