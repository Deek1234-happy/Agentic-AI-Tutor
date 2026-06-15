/**
 * useSubjectDocuments — fetches documents belonging to a specific subject.
 *
 * AUTO-POLLING:
 * When any document has status PENDING or PROCESSING (Hangfire job running),
 * TanStack Query automatically re-fetches every 3 seconds until all documents
 * reach COMPLETED or FAILED — then polling stops automatically.
 *
 * Usage:
 *   const { data: documents, isLoading, hasInProgress } = useSubjectDocuments(subjectId);
 *
 * After upload/delete, invalidate:
 *   queryClient.invalidateQueries({ queryKey: subjectDocumentsKey(subjectId) });
 */

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { getDocumentsBySubject } from "../services/documentService";
import type { DocumentResponse } from "../types/subject";

export const subjectDocumentsKey = (subjectId: string) =>
  ["documents", "by-subject", subjectId] as const;

const ACTIVE = new Set(["PENDING", "PROCESSING"]);

/**
 * A document is still "in progress" (and needs polling) if:
 * - processingStatus is PENDING or PROCESSING, OR
 * - kgStatus is PENDING or PROCESSING
 * (meaning one or both stages haven't settled yet)
 */
function isDocInProgress(doc: DocumentResponse): boolean {
  const ps = (doc.processingStatus ?? "").toUpperCase();
  const kg = (doc.kgStatus ?? "").toUpperCase();
  return ACTIVE.has(ps) || ACTIVE.has(kg);
}

export function useSubjectDocuments(subjectId: string | undefined) {
  const { session } = useAuth();

  const query = useQuery<DocumentResponse[], Error>({
    queryKey: subjectDocumentsKey(subjectId ?? ""),
    queryFn: () => getDocumentsBySubject(subjectId!),
    enabled: !!session && !!subjectId,
    staleTime: 0,           // always considered stale so invalidation always re-fetches
    gcTime: 5 * 60 * 1000,

    // ── Smart polling for Hangfire background jobs ───────────────────────────
    // This function is called by TanStack Query after every successful fetch.
    // Return a ms interval to schedule the next poll, or `false` to stop.
    refetchInterval: (queryArg) => {
      const docs = queryArg.state.data;
      if (!docs || docs.length === 0) return false;
      // Poll while any document has an active stage (chunking OR KG ingestion)
      const anyInProgress = docs.some(isDocInProgress);
      return anyInProgress ? 3_000 : false;   // poll every 3 s while processing
    },
    // Pause polling when the user switches to another browser tab
    refetchIntervalInBackground: false,
  });

  // Derived flag — true while any doc has an active stage (chunking OR KG ingestion)
  const hasInProgress = (query.data ?? []).some(isDocInProgress);

  return { ...query, hasInProgress };
}
