/**
 * useSubjects — fetches and caches the user's subject list.
 *
 * Usage:
 *   const { data: subjects, isLoading, isError } = useSubjects();
 *
 * After creating/deleting a subject, invalidate this key:
 *   queryClient.invalidateQueries({ queryKey: SUBJECTS_QUERY_KEY });
 */

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { getSubjects } from "../services/subjectService";
import type { SubjectResponse } from "../types/subject";

export const SUBJECTS_QUERY_KEY = ["subjects"] as const;

export function useSubjects() {
  const { session } = useAuth();

  return useQuery<SubjectResponse[], Error>({
    queryKey: SUBJECTS_QUERY_KEY,
    queryFn: getSubjects,
    enabled: !!session,
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}
