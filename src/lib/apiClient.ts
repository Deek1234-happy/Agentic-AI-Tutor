/**
 * Lightweight API client.
 * - Automatically reads the JWT from localStorage and attaches it as
 *   `Authorization: Bearer <token>` for every request that needs it.
 * - On non-2xx responses it extracts the plain-text or JSON error body
 *   and throws a plain `Error` so callers only need one catch branch.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5099";

// ─── Token helpers ────────────────────────────────────────────────────────────

const TOKEN_KEY = "auth_token";

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Session helpers (full AuthResponse subset) ───────────────────────────────

const SESSION_KEY = "auth_session";

export function saveSession(session: object): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function getSession<T>(): T | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
  removeToken();
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

interface RequestOptions {
  /** Whether to attach the stored JWT (default: false) */
  auth?: boolean;
  /** Extra headers merged on top of the defaults */
  headers?: Record<string, string>;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...options.headers,
  };

  if (options.auth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    // ── Global 401 handler ─────────────────────────────────────────────────
    // If the JWT is missing or has expired the backend returns 401.
    // Clear the stale session and redirect to the landing page so the user
    // can log in again instead of seeing broken/empty UI.
    if (response.status === 401) {
      clearSession();
      window.location.href = "/";
      // Throw so callers' catch blocks still run (they won't render after redirect anyway)
      throw new Error("Session expired. Please log in again.");
    }

    // The backend returns plain-text strings for 400 and other error codes
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  // Some endpoints return 200 with a plain string body — handle gracefully
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}

// ─── Convenience methods ──────────────────────────────────────────────────────

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>("GET", path, undefined, options),

  post: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>("POST", path, body, options),

  put: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>("PUT", path, body, options),

  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>("DELETE", path, undefined, options),
};
