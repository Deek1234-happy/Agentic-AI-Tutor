import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import {
  Upload, FileText, Trash2, CheckCircle2, Clock, XCircle,
  Loader2, RefreshCw, AlertCircle, Download, Eye, Network, Plus,
} from "lucide-react";
import { useSubjectDocuments, subjectDocumentsKey } from "../../../hooks/useSubjectDocuments";
import {
  uploadDocument,
  deleteDocument,
  retryDocumentProcessing,
  downloadDocument,
  getDocumentViewUrl,
} from "../../../services/documentService";
import { useAuth } from "../../../context/AuthContext";
import { USER_PROFILE_QUERY_KEY } from "../../../hooks/useUserProfile";
import type { DocumentResponse } from "../../../types/subject";

// ─── Two-stage status derivation ─────────────────────────────────────────────
//
// A document goes through TWO sequential pipeline stages:
//   1. processingStatus — text chunking job (Hangfire)
//   2. kgStatus         — Knowledge Graph ingestion (after chunking completes)
//
// The document is only truly COMPLETED when BOTH stages finish successfully.
// If EITHER fails, the document is FAILED and the Retry button is shown.

type CombinedStatus =
  | "PENDING"        // chunking not yet started
  | "PROCESSING"     // chunking in progress
  | "KG_PROCESSING"  // chunking done, KG ingestion running
  | "COMPLETED"      // both stages done
  | "FAILED";        // one or both stages failed

interface StatusConfig {
  icon: React.ElementType;
  label: string;
  color: string;
  spinning: boolean;
}

const STATUS_CONFIG: Record<CombinedStatus, StatusConfig> = {
  PENDING:       { icon: Clock,        label: "Pending",       color: "bg-gray-100 text-gray-600",   spinning: false },
  PROCESSING:    { icon: Loader2,      label: "Processing",    color: "bg-blue-100 text-blue-600",   spinning: true  },
  KG_PROCESSING: { icon: Network,      label: "Building KG…",  color: "bg-violet-100 text-violet-600", spinning: true  },
  COMPLETED:     { icon: CheckCircle2, label: "Completed",     color: "bg-green-100 text-green-600", spinning: false },
  FAILED:        { icon: XCircle,      label: "Failed",        color: "bg-red-100 text-red-600",     spinning: false },
};

/**
 * Derives the combined display status from both pipeline fields.
 *
 * Priority:
 *   1. If either field is FAILED → FAILED (show Retry)
 *   2. If both are COMPLETED    → COMPLETED (show View + Download)
 *   3. If chunking done, KG still running/pending → KG_PROCESSING
 *   4. Otherwise → PROCESSING / PENDING based on processingStatus
 */
function getCombinedStatus(doc: DocumentResponse): CombinedStatus {
  const ps = (doc.processingStatus ?? "").toUpperCase();
  const kg = (doc.kgStatus ?? "").toUpperCase();

  // Either stage failed
  if (ps === "FAILED" || kg === "FAILED") return "FAILED";

  // Both stages finished
  if (ps === "COMPLETED" && kg === "COMPLETED") return "COMPLETED";

  // Chunking finished; KG not yet done (PENDING, PROCESSING, or null/empty)
  if (ps === "COMPLETED") return "KG_PROCESSING";

  // Chunking still running
  if (ps === "PROCESSING") return "PROCESSING";

  // Default: chunking hasn't started
  return "PENDING";
}

// ─── File size formatter ──────────────────────────────────────────────────────

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── Table row skeleton ───────────────────────────────────────────────────────

function DocRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 7 }).map((_, i) => (
        <TableCell key={i}><Skeleton className="h-4 w-full" /></TableCell>
      ))}
    </TableRow>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface DocumentsTabProps {
  subjectId: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function DocumentsTab({ subjectId }: DocumentsTabProps) {
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Hook auto-polls every 3 s when any document is PENDING/PROCESSING
  const { data: documents, isLoading, isError, hasInProgress, isFetching } =
    useSubjectDocuments(subjectId);

  // Upload state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState<DocumentResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Per-document action tracking
  const [retrying, setRetrying] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [viewing, setViewing] = useState<string | null>(null);
  
  // Viewer state
  const [viewingDocUrl, setViewingDocUrl] = useState<string | null>(null);
  const [viewingDocName, setViewingDocName] = useState<string | null>(null);

  // ── Upload ────────────────────────────────────────────────────────────────

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (!session?.userId) { toast.error("No active session."); return; }

    setUploadError(null);
    setIsUploading(true);

    try {
      for (const file of Array.from(files)) {
        await uploadDocument({ userId: session.userId, subjectId, file });
        toast.success(`"${file.name}" uploaded. Processing queued.`);
      }
      // Invalidate — the hook will then auto-poll because the new doc is PENDING
      await queryClient.invalidateQueries({ queryKey: subjectDocumentsKey(subjectId) });
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed.";
      setUploadError(msg);
      toast.error(msg);
    } finally {
      setIsUploading(false);
      setUploadOpen(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  // ── Delete ────────────────────────────────────────────────────────────────

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteDocument(deleteTarget.id);
      toast.success(`"${deleteTarget.fileName}" deleted.`);
      await queryClient.invalidateQueries({ queryKey: subjectDocumentsKey(subjectId) });
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      setDeleteTarget(null);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to delete document.");
    } finally {
      setIsDeleting(false);
    }
  };

  // ── Retry ─────────────────────────────────────────────────────────────────

  const handleRetry = async (doc: DocumentResponse) => {
    setRetrying(doc.id);
    try {
      await retryDocumentProcessing(doc.id);
      toast.success(`Retrying processing for "${doc.fileName}".`);
      await queryClient.invalidateQueries({ queryKey: subjectDocumentsKey(subjectId) });
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Retry failed.");
    } finally {
      setRetrying(null);
    }
  };

  // ── Download ──────────────────────────────────────────────────────────────

  const handleDownload = async (doc: DocumentResponse) => {
    setDownloading(doc.id);
    try {
      await downloadDocument(doc.id, doc.fileName ?? "document");
      toast.success(`Downloading "${doc.fileName}"…`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloading(null);
    }
  };

  // ── View (inline) ──────────────────────────────────────────────────────────

  const handleView = async (doc: DocumentResponse) => {
    setViewing(doc.id);
    try {
      const url = await getDocumentViewUrl(doc.id);
      setViewingDocUrl(url);
      setViewingDocName(doc.fileName ?? "Document");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Could not open document.");
    } finally {
      setViewing(null);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <TooltipProvider>
      <div className="space-y-6">

        {/* ── Hangfire processing banner ─────────────────────────────────── */}
        {hasInProgress && (
          <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
            <Loader2 className="w-4 h-4 animate-spin shrink-0" />
            <div>
              <span className="font-medium">Processing in progress</span>
              <span className="text-blue-600"> — Hangfire is extracting and indexing your documents. This page updates automatically every 3 s.</span>
            </div>
            {isFetching && !isLoading && (
              <span className="ml-auto text-xs text-blue-400 shrink-0">Refreshing…</span>
            )}
          </div>
        )}

        {/* ── Documents table ───────────────────────────────────────────── */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Uploaded Documents</CardTitle>
              <CardDescription>
                {isLoading
                  ? "Loading…"
                  : `${documents?.length ?? 0} document${documents?.length === 1 ? "" : "s"} in this subject`}
              </CardDescription>
            </div>
            
            <Dialog open={uploadOpen} onOpenChange={(o) => { if (!isUploading) setUploadOpen(o); }}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="w-4 h-4 mr-2" /> Add Document
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Upload Documents</DialogTitle>
                  <DialogDescription>
                    Upload study materials to this subject. Max 10 MB per file.
                  </DialogDescription>
                </DialogHeader>
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                    isDragging
                      ? "border-primary bg-primary/5"
                      : "border-gray-300 hover:border-primary/50"
                  }`}
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-10 h-10 mx-auto mb-4 text-primary animate-spin" />
                      <h3 className="text-base mb-2 font-medium">Uploading…</h3>
                      <p className="text-sm text-muted-foreground">Please wait.</p>
                    </>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 mx-auto mb-4 text-muted-foreground" />
                      <h3 className="text-base mb-2 font-medium">Drop files here or click</h3>
                      <Button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        variant="secondary"
                      >
                        Select Files
                      </Button>
                    </>
                  )}
                </div>
                {uploadError && (
                  <div className="flex items-start gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    {uploadError}
                  </div>
                )}
              </DialogContent>
            </Dialog>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.pptx,.xlsx"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </CardHeader>
          <CardContent>
            {isError && (
              <div className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2 mb-4">
                Failed to load documents. Please refresh.
              </div>
            )}

            {!isError && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>File Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading
                    ? Array.from({ length: 3 }).map((_, i) => <DocRowSkeleton key={i} />)
                    : documents && documents.length === 0
                    ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                          No documents yet. Upload your first file above.
                        </TableCell>
                      </TableRow>
                    )
                    : documents?.map((doc) => {
                      // Derive the unified status from BOTH pipeline stages
                      const combined       = getCombinedStatus(doc);
                      const { icon: StatusIcon, label, color, spinning } = STATUS_CONFIG[combined];

                      const isTrulyCompleted = combined === "COMPLETED";
                      const hasFailed        = combined === "FAILED";
                      const isInProgress     = combined === "PROCESSING" || combined === "KG_PROCESSING" || combined === "PENDING";

                      return (
                        <TableRow key={doc.id} className={isInProgress ? "bg-blue-50/30" : ""}>
                          <TableCell className="font-medium max-w-[200px]">
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                              {isTrulyCompleted ? (
                                <button
                                  type="button"
                                  disabled={viewing === doc.id}
                                  onClick={() => handleView(doc)}
                                  className="truncate text-left hover:underline hover:text-primary transition-colors focus:outline-none flex items-center gap-2"
                                  title="View document"
                                >
                                  <span className="truncate">{doc.fileName ?? "—"}</span>
                                  {viewing === doc.id && <Loader2 className="w-3 h-3 animate-spin text-primary shrink-0" />}
                                </button>
                              ) : (
                                <span className="truncate">{doc.fileName ?? "—"}</span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {doc.fileType?.replace(".", "").toUpperCase() ?? "—"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatBytes(doc.fileSize)}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {doc.uploadTime
                              ? new Date(doc.uploadTime).toLocaleDateString("en-US", {
                                  month: "short", day: "numeric", year: "numeric",
                                })
                              : "—"}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary" className={color}>
                              <StatusIcon
                                className={`w-3 h-3 mr-1 ${spinning ? "animate-spin" : ""}`}
                              />
                              {label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">


                              {/* ── Download — only when BOTH stages completed ── */}
                              {isTrulyCompleted && (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      disabled={downloading === doc.id}
                                      onClick={() => handleDownload(doc)}
                                    >
                                      {downloading === doc.id
                                        ? <Loader2 className="w-4 h-4 animate-spin" />
                                        : <Download className="w-4 h-4 text-green-600" />
                                      }
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Download file</TooltipContent>
                                </Tooltip>
                              )}

                              {/* ── Retry — when processingStatus OR kgStatus is FAILED ── */}
                              {hasFailed && (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      disabled={retrying === doc.id}
                                      onClick={() => handleRetry(doc)}
                                    >
                                      {retrying === doc.id
                                        ? <Loader2 className="w-4 h-4 animate-spin" />
                                        : <RefreshCw className="w-4 h-4 text-orange-500" />
                                      }
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Retry processing</TooltipContent>
                                </Tooltip>
                              )}

                              {/* ── Delete — always available ── */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => setDeleteTarget(doc)}
                                  >
                                    <Trash2 className="w-4 h-4 text-destructive" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Delete document</TooltipContent>
                              </Tooltip>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

      {/* ── Delete confirmation ───────────────────────────────────────── */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{deleteTarget?.fileName}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the document and all associated AI Knowledge Graph
              data. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Deleting…</> : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Full Screen Document Viewer ───────────────────────────────── */}
      {viewingDocUrl && (
        <div className="fixed inset-0 z-[100] bg-background flex flex-col w-screen h-[100dvh]">
          {/* Header */}
          <div className="flex items-center justify-between py-2 px-4 border-b shrink-0 bg-card">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" />
              <h2 className="text-base font-medium capitalize truncate max-w-[500px]">
                {viewingDocName}
              </h2>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant="default"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => {
                    if (viewingDocUrl) URL.revokeObjectURL(viewingDocUrl);
                    setViewingDocUrl(null);
                    setViewingDocName(null);
                  }}
                >
                  <XCircle className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Close viewer</TooltipContent>
            </Tooltip>
          </div>
          
          {/* Iframe */}
          <div className="flex-1 w-full overflow-hidden bg-muted">
            <iframe 
              src={viewingDocUrl} 
              className="w-full h-full border-0" 
              title="Document Viewer" 
            />
          </div>
        </div>
      )}
    </div>
  </TooltipProvider>
);
}
