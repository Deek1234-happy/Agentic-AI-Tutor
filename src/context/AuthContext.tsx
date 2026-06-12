/**
 * AuthContext — manages ONLY the JWT session (userId + token).
 *
 * Profile data (firstName, lastName, stats…) is handled separately by
 * the `useUserProfile()` hook (TanStack Query), keeping this context
 * small and focused on a single responsibility.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSession, clearSession } from "../lib/apiClient";
import type { StoredSession } from "../types/auth";

// ─── Shape ────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  /** JWT session; null when logged out */
  session: StoredSession | null;
  /** Call after a successful login/register to hydrate context */
  setSession: (session: StoredSession) => void;
  /** Clears localStorage and resets all context state */
  logout: () => void;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSessionState] = useState<StoredSession | null>(
    () => getSession<StoredSession>()
  );

  const setSession = useCallback((s: StoredSession) => {
    setSessionState(s);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setSessionState(null);
    queryClient.clear();
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ session, setSession, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
