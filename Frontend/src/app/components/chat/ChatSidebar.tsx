import { useState } from "react";
import { Plus, MoreVertical, Edit2, Trash2, MessageSquare } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { useChatSessions } from "../../../hooks/useChat";
import { formatDistanceToNow } from "date-fns";

interface ChatSidebarProps {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
}

export function ChatSidebar({ activeSessionId, onSelectSession, onNewChat }: ChatSidebarProps) {
  const { data: sessions, renameSession, deleteSession } = useChatSessions();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  const handleRenameSubmit = (sessionId: string) => {
    if (editTitle.trim() !== "") {
      renameSession.mutate({ sessionId, title: editTitle.trim() });
    }
    setEditingId(null);
  };

  return (
    <div className="h-full w-full flex flex-col">
      <div className="border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-primary" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold tracking-tight truncate">Chat history</div>
              <div className="text-xs text-muted-foreground truncate">
                {sessions?.length ? `${sessions.length} session${sessions.length === 1 ? "" : "s"}` : "No sessions yet"}
              </div>
            </div>
          </div>

          <Button
            onClick={onNewChat}
            className="w-full rounded-full shadow-sm hover:shadow transition-all duration-200"
            size="sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            New chat
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {sessions?.map((session) => (
            <div
              key={session.id}
              className={`group relative rounded-xl px-3 py-2 cursor-pointer transition-all duration-200 border ${
                activeSessionId === session.id
                  ? "bg-background border-primary/20 shadow-sm"
                  : "bg-transparent border-transparent hover:bg-background hover:border-border"
              }`}
              onClick={() => onSelectSession(session.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelectSession(session.id);
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  {editingId === session.id ? (
                    <Input
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleRenameSubmit(session.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      onBlur={() => handleRenameSubmit(session.id)}
                      className="h-8 text-sm"
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <h3
                      className={`text-sm truncate ${
                        activeSessionId === session.id ? "text-foreground font-medium" : "text-foreground/90"
                      }`}
                      title={session.title}
                    >
                      {session.title || "Untitled Chat"}
                    </h3>
                  )}
                  <span className="text-[11px] text-muted-foreground">
                    {formatDistanceToNow(new Date(session.updatedAt), { addSuffix: true })}
                  </span>
                </div>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity duration-200"
                      title="Session actions"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-40">
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(session.id);
                        setEditTitle(session.title);
                      }}
                    >
                      <Edit2 className="w-4 h-4 mr-2" />
                      Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget({ id: session.id, title: session.title || "Untitled Chat" });
                      }}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          ))}

          {(!sessions || sessions.length === 0) && (
            <div className="px-3 py-10 text-center">
              <div className="mx-auto w-10 h-10 rounded-2xl bg-muted flex items-center justify-center mb-3">
                <MessageSquare className="w-5 h-5 text-muted-foreground" />
              </div>
              <div className="text-sm font-medium">No chats yet</div>
              <p className="text-sm text-muted-foreground mt-1">
                Create your first chat session to get started.
              </p>
            </div>
          )}
        </div>
      </div>

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{deleteTarget?.title}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the chat session and its messages from your history.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteSession.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleteSession.isPending}
              onClick={() => {
                if (!deleteTarget) return;
                deleteSession.mutate(deleteTarget.id, {
                  onSettled: () => setDeleteTarget(null),
                });
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
