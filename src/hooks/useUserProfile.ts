/**
 * useUserProfile — fetches and caches the authenticated user's full profile.
 *
 * Built on TanStack Query so data is:
 *  - Cached globally (no duplicate API calls across components)
 *  - Auto-refreshed in the background on window focus
 *  - Only fetched when a valid session exists (enabled: !!session)
 *
 * Usage:
 *   const { data: profile, isLoading, isError, refetch } = useUserProfile();
 *
 * Invalidate/refresh after a settings update:
 *   const queryClient = useQueryClient();
 *   queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
 */

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { getUserProfile } from "../services/userService";
import type { UserResponse } from "../types/user";

export const USER_PROFILE_QUERY_KEY = ["user", "profile"] as const;

export function useUserProfile() {
  const { session } = useAuth();

  return useQuery<UserResponse, Error>({
    queryKey: USER_PROFILE_QUERY_KEY,
    queryFn: getUserProfile,
    // Only run when the user has a valid session
    enabled: !!session,
    // Keep data fresh for 5 minutes before a background refetch
    staleTime: 5 * 60 * 1000,
    // Retain cached data for 10 minutes after the component unmounts
    gcTime: 10 * 60 * 1000,
  });
}
