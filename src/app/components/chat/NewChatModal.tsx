import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Checkbox } from "../ui/checkbox";
import { Alert, AlertDescription } from "../ui/alert";
import { Book, FileText, Loader2 } from "lucide-react";
import { useSubjects } from "../../../hooks/useSubjects";
import { useSubjectDocuments } from "../../../hooks/useSubjectDocuments";
import { useChatSessions } from "../../../hooks/useChat";
// Replaced missing getCombinedStatus import

interface NewChatModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChatCreated: (sessionId: string) => void;
}

export function NewChatModal({ open, onOpenChange, onChatCreated }: NewChatModalProps) {
  const { data: subjects, isLoading: isLoadingSubjects } = useSubjects();
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  
  const { data: documents, isLoading: isLoadingDocs } = useSubjectDocuments(selectedSubjectId || undefined);
  const { createSession } = useChatSessions();

  // Filter only fully processed documents
  const availableDocs = documents?.filter(d => d.processingStatus === "COMPLETED" && d.kgStatus === "COMPLETED") || [];

  const handleCreate = () => {
    if (!selectedSubjectId || selectedDocIds.length === 0) return;
    
    createSession.mutate({ documentIds: selectedDocIds }, {
      onSuccess: (newSession) => {
        onChatCreated(newSession.id);
        onOpenChange(false);
        // Reset state
        setSelectedSubjectId("");
        setSelectedDocIds([]);
      }
    });
  };

  const handleDocToggle = (docId: string) => {
    setSelectedDocIds(prev => 
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  const selectedSubject = subjects?.find(s => s.id === selectedSubjectId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Start New Chat Session</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Subject Selector */}
          <div className="space-y-2">
            <Label>Select Subject</Label>
            <Select 
              value={selectedSubjectId} 
              onValueChange={(val) => {
                setSelectedSubjectId(val);
                setSelectedDocIds([]); // Reset docs on subject change
              }}
              disabled={isLoadingSubjects}
            >
              <SelectTrigger>
                <SelectValue placeholder="Choose a subject for this chat" />
              </SelectTrigger>
              <SelectContent>
                {subjects?.map((subject) => (
                  <SelectItem key={subject.id} value={subject.id} className="capitalize">
                    {subject.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Document Multi-Select */}
          {selectedSubjectId && (
            <div className="space-y-2">
              <Label>Select Documents ({selectedDocIds.length} selected)</Label>
              <div className="border rounded-lg p-4 space-y-3 max-h-64 overflow-y-auto">
                {isLoadingDocs ? (
                  <div className="flex justify-center p-4">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : availableDocs.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No fully processed documents found in this subject.
                  </p>
                ) : (
                  availableDocs.map((doc) => (
                    <div key={doc.id} className="flex items-start space-x-3">
                      <Checkbox
                        id={`doc-${doc.id}`}
                        checked={selectedDocIds.includes(doc.id)}
                        onCheckedChange={() => handleDocToggle(doc.id)}
                      />
                      <label
                        htmlFor={`doc-${doc.id}`}
                        className="flex-1 flex items-center gap-2 text-sm cursor-pointer"
                      >
                        <FileText className="w-4 h-4 text-muted-foreground" />
                        <span className="truncate">{doc.fileName}</span>
                      </label>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Context Preview */}
          {selectedSubjectId && selectedDocIds.length > 0 && (
            <Alert className="bg-primary/5 border-primary/20">
              <Book className="w-4 h-4 text-primary" />
              <AlertDescription>
                <span className="font-medium">This chat will be scoped to:</span>{" "}
                <span className="text-primary font-semibold capitalize">
                  {selectedSubject?.name}
                </span>
                {" → "}
                <span className="text-muted-foreground">
                  {selectedDocIds.length} document(s)
                </span>
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleCreate}
            disabled={!selectedSubjectId || selectedDocIds.length === 0 || createSession.isPending}
          >
            {createSession.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
            Start Chat
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
