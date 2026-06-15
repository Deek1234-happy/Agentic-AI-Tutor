import { useState } from "react";
import { Link } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Plus, FileText, MoreVertical, Trash2, BookOpen, Loader2, Pencil,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { useSubjects, SUBJECTS_QUERY_KEY } from "../../hooks/useSubjects";
import { createSubject, deleteSubject, updateSubject } from "../../services/subjectService";
import { USER_PROFILE_QUERY_KEY } from "../../hooks/useUserProfile";

const PALETTE = [
  "bg-blue-500", "bg-purple-500", "bg-green-500", "bg-yellow-500",
  "bg-pink-500", "bg-indigo-500", "bg-red-500", "bg-teal-500",
];

function subjectColor(index: number) {
  return PALETTE[index % PALETTE.length];
}

function SubjectCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div className="flex items-start justify-between">
          <Skeleton className="w-12 h-12 rounded-xl" />
          <Skeleton className="w-8 h-8 rounded-md" />
        </div>
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-9 w-full rounded-md" />
      </CardContent>
    </Card>
  );
}

export default function Subjects() {
  const queryClient = useQueryClient();
  const { data: subjects, isLoading, isError } = useSubjects();

  const [createOpen, setCreateOpen] = useState(false);
  const [subjectName, setSubjectName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [renameTarget, setRenameTarget] = useState<{ id: string; name: string } | null>(null);
  const [renameName, setRenameName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameError, setRenameError] = useState<string | null>(null);

  const openRenameDialog = (subject: { id: string; name: string | null }) => {
    setRenameTarget({ id: subject.id, name: subject.name ?? "" });
    setRenameName(subject.name ?? "");
    setRenameError(null);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!subjectName.trim()) {
      setCreateError("Subject name is required.");
      return;
    }

    setIsCreating(true);
    try {
      await createSubject({ name: subjectName.trim() });
      toast.success(`Subject "${subjectName.trim()}" created!`);
      await queryClient.invalidateQueries({ queryKey: SUBJECTS_QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      setSubjectName("");
      setCreateOpen(false);
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create subject.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleRenameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRenameError(null);
    if (!renameName.trim()) {
      setRenameError("Name cannot be empty.");
      return;
    }
    if (!renameTarget) return;

    setIsRenaming(true);
    try {
      await updateSubject(renameTarget.id, { name: renameName.trim() });
      toast.success(`Subject renamed to "${renameName.trim()}".`);
      await queryClient.invalidateQueries({ queryKey: SUBJECTS_QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: ["subject", renameTarget.id] });
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      setRenameTarget(null);
    } catch (err: unknown) {
      setRenameError(err instanceof Error ? err.message : "Failed to rename subject.");
    } finally {
      setIsRenaming(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteSubject(deleteTarget.id);
      toast.success(`Subject "${deleteTarget.name}" deleted.`);
      await queryClient.invalidateQueries({ queryKey: SUBJECTS_QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      setDeleteTarget(null);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to delete subject.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl mb-2">My Subjects</h1>
          <p className="text-muted-foreground">Organize and manage your learning materials</p>
        </div>

        <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); setCreateError(null); setSubjectName(""); }}>
          <DialogTrigger asChild>
            <Button id="btn-create-subject">
              <Plus className="w-4 h-4 mr-2" />
              Create Subject
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Subject</DialogTitle>
              <DialogDescription>
                Add a new subject to organize your study materials. Every document must belong to a subject.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subjectName">Subject Name</Label>
                <Input
                  id="subjectName"
                  placeholder="e.g., Advanced Mathematics"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  disabled={isCreating}
                  maxLength={255}
                  required
                />
              </div>
              {createError && (
                <p role="alert" className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                  {createError}
                </p>
              )}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} disabled={isCreating}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isCreating} id="btn-create-subject-submit">
                  {isCreating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Creating...</> : "Create Subject"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isError && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load subjects. Please refresh the page.
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => <SubjectCardSkeleton key={i} />)
          : subjects && subjects.length === 0
          ? (
            <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
              <BookOpen className="w-16 h-16 text-muted-foreground/30 mb-4" />
              <h3 className="text-lg font-medium mb-2">No subjects yet</h3>
              <p className="text-muted-foreground text-sm mb-6">
                Create your first subject to start uploading documents.
              </p>
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Subject
              </Button>
            </div>
          )
          : subjects?.map((subject, index) => (
            <Card key={subject.id} className="hover:shadow-lg transition-shadow group">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 ${subjectColor(index)} rounded-xl flex items-center justify-center`}>
                    <FileText className="w-6 h-6 text-white" />
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity"
                        aria-label={`Open actions for ${subject.name ?? "subject"}`}
                      >
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openRenameDialog(subject)}>
                        <Pencil className="w-4 h-4 mr-2" />
                        Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => setDeleteTarget({ id: subject.id, name: subject.name ?? "this subject" })}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete Subject
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="mb-3 flex min-h-7 items-start gap-2">
                  <Link to={`/dashboard/subjects/${subject.id}`} className="min-w-0 flex-1">
                    <h3 className="text-lg hover:text-primary transition-colors font-medium capitalize truncate">
                      {subject.name}
                    </h3>
                  </Link>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0 text-muted-foreground opacity-70 hover:opacity-100"
                    onClick={() => openRenameDialog(subject)}
                    aria-label={`Rename ${subject.name ?? "subject"}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </div>

                <div className="flex items-center justify-between text-sm mb-4">
                  <span className="text-muted-foreground">Documents</span>
                  <Badge variant="secondary">{subject.documents?.length ?? 0}</Badge>
                </div>

                <Link to={`/dashboard/subjects/${subject.id}`}>
                  <Button variant="outline" className="w-full">Open Subject</Button>
                </Link>
              </CardContent>
            </Card>
          ))}
      </div>

      <Dialog
        open={!!renameTarget}
        onOpenChange={(open) => {
          if (!open) {
            setRenameTarget(null);
            setRenameError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Subject</DialogTitle>
            <DialogDescription>
              Enter a new name for "{renameTarget?.name}".
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleRenameSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="renameName">New Name</Label>
              <Input
                id="renameName"
                value={renameName}
                onChange={(e) => setRenameName(e.target.value)}
                disabled={isRenaming}
                maxLength={255}
                required
                autoFocus
              />
            </div>
            {renameError && (
              <p role="alert" className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                {renameError}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setRenameTarget(null)} disabled={isRenaming}>
                Cancel
              </Button>
              <Button type="submit" disabled={isRenaming}>
                {isRenaming ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</> : "Save"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{deleteTarget?.name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the subject and <strong>all documents</strong> inside it,
              including their AI Knowledge Graph data. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Deleting...</> : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
