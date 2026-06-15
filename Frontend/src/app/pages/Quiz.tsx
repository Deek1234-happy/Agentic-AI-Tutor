import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { BookOpen, Eye, Loader2, RefreshCw, Sparkles, Trophy } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Checkbox } from "../components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { checkStatus, getQuizHistory, initiateQuiz } from "../../services/quizService";
import type { QuizHistoryItem } from "../../types/quiz";
import { useSubjects } from "../../hooks/useSubjects";
import { useSubjectDocuments } from "../../hooks/useSubjectDocuments";
import type { DocumentResponse } from "../../types/subject";

export default function Quiz() {
  const navigate = useNavigate();
  const pollingRef = useRef<number | null>(null);
  const pollingQuizIdsRef = useRef<Set<string>>(new Set());
  const [history, setHistory] = useState<QuizHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [subjectId, setSubjectId] = useState("");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [questionCount, setQuestionCount] = useState("10");
  const [historySubjectId, setHistorySubjectId] = useState("all");
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize, setHistoryPageSize] = useState(10);
  const { data: subjects = [], isLoading: isLoadingSubjects } = useSubjects();
  const {
    data: subjectDocuments = [],
    isLoading: isLoadingDocuments,
    hasInProgress,
  } = useSubjectDocuments(subjectId || undefined);

  useEffect(() => {
    loadHistory();
    return stopPolling;
  }, [historySubjectId, historyPage, historyPageSize]);

  const stopPolling = () => {
    if (pollingRef.current) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    pollingQuizIdsRef.current.clear();
  };

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      const quizzes = await getQuizHistory({
        subjectId: historySubjectId === "all" ? undefined : historySubjectId,
        page: historyPage,
        pageSize: historyPageSize,
      });
      setHistory(quizzes);
      quizzes
        .filter((quiz) => quiz.status?.toUpperCase() === "GENERATING")
        .forEach((quiz) => pollQuizStatus(quiz.quizId));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load quiz history.";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!subjectId.trim()) {
      toast.error("Please select a subject.");
      return;
    }

    if (selectedDocumentIds.length === 0) {
      toast.error("Please select at least one ready document.");
      return;
    }

    const count = Number(questionCount);
    if (!Number.isInteger(count) || count < 1) {
      toast.error("Question count must be at least 1.");
      return;
    }

    setIsGenerating(true);
    try {
      const selectedSubject = subjects.find((subject) => subject.id === subjectId);
      const response = await initiateQuiz({
        subjectId: subjectId.trim(),
        documentIds: selectedDocumentIds,
        numberOfQuestions: count,
      });

      const normalizedStatus = response.status?.toUpperCase() || "GENERATING";
      setHistory((previous) => upsertQuiz(previous, {
        quizId: response.quizId,
        status: response.status || "GENERATING",
        subjectId: subjectId.trim(),
        subjectName: selectedSubject?.name ?? "Selected subject",
        questionCount: count,
        createdAt: new Date().toISOString(),
        attemptCount: 0,
        bestScore: null,
      }));

      if (response.status?.toUpperCase() === "READY") {
        toast.success(response.message || "Quiz is ready.");
        setIsDialogOpen(false);
        setSelectedDocumentIds([]);
        setIsGenerating(false);
        return;
      }

      toast.success(response.message || "Quiz generation started.");
      setIsDialogOpen(false);
      setSelectedDocumentIds([]);
      setIsGenerating(false);
      pollQuizStatus(response.quizId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to generate quiz.";
      setIsGenerating(false);
      toast.error(message);
    }
  };

  const pollQuizStatus = (quizId: string) => {
    pollingQuizIdsRef.current.add(quizId);
    if (pollingRef.current) return;

    pollingRef.current = window.setInterval(async () => {
      const quizIds = Array.from(pollingQuizIdsRef.current);
      if (quizIds.length === 0) {
        stopPolling();
        return;
      }

      try {
        const statuses = await Promise.all(quizIds.map((id) => checkStatus(id)));

        statuses.forEach((status) => {
          const normalizedStatus = status.status?.toUpperCase();

          setHistory((previous) =>
            previous.map((quiz) =>
              quiz.quizId === status.quizId
                ? { ...quiz, status: status.status, questionCount: status.questionCount || quiz.questionCount }
                : quiz
            )
          );

          if (normalizedStatus === "READY") {
            pollingQuizIdsRef.current.delete(status.quizId);
            toast.success("A quiz is ready to take.");
            loadHistory();
          }

          if (normalizedStatus === "FAILED") {
            pollingQuizIdsRef.current.delete(status.quizId);
            toast.error("Quiz generation failed. Please try again.");
            loadHistory();
          }
        });
      } catch (err) {
        stopPolling();
        const message = err instanceof Error ? err.message : "Unable to check quiz status.";
        toast.error(message);
      }
    }, 4000);
  };

  const formatDate = (value: string | null) => {
    if (!value) return "Not available";
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  };

  const formatScore = (value: number | null) => {
    if (value === null || value === undefined) return "No attempts";
    return `${Math.round(value)}%`;
  };

  const handleSubjectChange = (value: string) => {
    setSubjectId(value);
    setSelectedDocumentIds([]);
  };

  const handleDocumentToggle = (documentId: string, checked: boolean) => {
    setSelectedDocumentIds((previous) =>
      checked ? [...previous, documentId] : previous.filter((id) => id !== documentId)
    );
  };

  const isDocumentReady = (document: DocumentResponse) => {
    return (
      document.processingStatus?.toUpperCase() === "COMPLETED" &&
      document.kgStatus?.toUpperCase() === "COMPLETED"
    );
  };

  const upsertQuiz = (quizzes: QuizHistoryItem[], quiz: QuizHistoryItem) => {
    const existingIndex = quizzes.findIndex((item) => item.quizId === quiz.quizId);
    if (existingIndex === -1) return [quiz, ...quizzes];

    return quizzes.map((item) => (item.quizId === quiz.quizId ? { ...item, ...quiz } : item));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl mb-2">Quizzes</h1>
          <p className="text-muted-foreground">Generate and review quizzes from your study materials.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadHistory} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={() => setIsDialogOpen(true)}>
            <Sparkles className="mr-2 h-4 w-4" />
            Generate New Quiz
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-primary" />
            Quiz History
          </CardTitle>
          <CardDescription>Your generated quizzes and best attempt scores.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Subject Filter</Label>
                <Select
                  value={historySubjectId}
                  onValueChange={(value) => {
                    setHistorySubjectId(value);
                    setHistoryPage(1);
                  }}
                  disabled={isLoadingSubjects}
                >
                  <SelectTrigger className="min-w-56">
                    <SelectValue placeholder="All subjects" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All subjects</SelectItem>
                    {subjects.map((subject) => (
                      <SelectItem key={subject.id} value={subject.id}>
                        {subject.name || "Untitled subject"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Rows Per Page</Label>
                <Select
                  value={historyPageSize.toString()}
                  onValueChange={(value) => {
                    setHistoryPageSize(Number(value));
                    setHistoryPage(1);
                  }}
                >
                  <SelectTrigger className="min-w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="25">25</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">Page {historyPage}</p>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading quizzes
            </div>
          ) : history.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BookOpen className="mb-4 h-10 w-10 text-muted-foreground" />
              <h3 className="font-semibold">No quizzes yet</h3>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                Generate a quiz from your processed documents to start testing your knowledge.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subject</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Questions</TableHead>
                  <TableHead>Attempts</TableHead>
                  <TableHead>Best Score</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((quiz) => {
                  const isReady = quiz.status?.toUpperCase() === "READY";
                  return (
                    <TableRow key={quiz.quizId}>
                      <TableCell className="font-medium">
                        {quiz.subjectId ? (
                          <button
                            type="button"
                            onClick={() => navigate(`/dashboard/subjects/${quiz.subjectId}`)}
                            className="max-w-[240px] truncate text-left text-primary underline-offset-4 hover:underline"
                            title={quiz.subjectName || "Open subject"}
                          >
                            {quiz.subjectName || "Untitled subject"}
                          </button>
                        ) : (
                          "Untitled subject"
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={isReady ? "default" : quiz.status?.toUpperCase() === "FAILED" ? "destructive" : "secondary"}>
                          {quiz.status?.toUpperCase() === "GENERATING" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                          {quiz.status || "Unknown"}
                        </Badge>
                      </TableCell>
                      <TableCell>{quiz.questionCount}</TableCell>
                      <TableCell>{quiz.attemptCount}</TableCell>
                      <TableCell>{formatScore(quiz.bestScore)}</TableCell>
                      <TableCell>{formatDate(quiz.createdAt)}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" disabled={!isReady} onClick={() => navigate(`/quizzes/${quiz.quizId}`)}>
                          <Eye className="mr-2 h-4 w-4" />
                          {isReady ? "Open" : "Generating"}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}

          <div className="flex items-center justify-between border-t pt-4">
            <Button
              variant="outline"
              onClick={() => setHistoryPage((page) => Math.max(1, page - 1))}
              disabled={isLoading || historyPage === 1}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Showing {history.length} quiz{history.length === 1 ? "" : "zes"}
            </span>
            <Button
              variant="outline"
              onClick={() => setHistoryPage((page) => page + 1)}
              disabled={isLoading || history.length < historyPageSize}
            >
              Next
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={(open) => !isGenerating && setIsDialogOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate New Quiz</DialogTitle>
            <DialogDescription>
              Select a subject, choose the ready documents to quiz from, then choose the number of questions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
              <div className="space-y-2">
                <Label>Subject</Label>
                <Select value={subjectId} onValueChange={handleSubjectChange} disabled={isLoadingSubjects}>
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingSubjects ? "Loading subjects..." : "Select a subject"} />
                  </SelectTrigger>
                  <SelectContent>
                    {subjects.map((subject) => (
                      <SelectItem key={subject.id} value={subject.id}>
                        {subject.name || "Untitled subject"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {subjectId && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <Label>Documents</Label>
                    <span className="text-xs text-muted-foreground">{selectedDocumentIds.length} selected</span>
                  </div>
                  <div className="max-h-64 overflow-y-auto rounded-lg border p-3">
                    {isLoadingDocuments ? (
                      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Loading documents
                      </div>
                    ) : subjectDocuments.length === 0 ? (
                      <p className="py-8 text-center text-sm text-muted-foreground">
                        No documents found for this subject.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {subjectDocuments.map((document) => {
                          const ready = isDocumentReady(document);
                          const checked = selectedDocumentIds.includes(document.id);

                          return (
                            <Label
                              key={document.id}
                              htmlFor={`quiz-document-${document.id}`}
                              className={`flex items-start gap-3 rounded-md border p-3 transition-colors ${
                                ready ? "cursor-pointer hover:bg-accent" : "cursor-not-allowed opacity-60"
                              } ${checked ? "border-primary bg-primary/5" : "border-border"}`}
                            >
                              <Checkbox
                                id={`quiz-document-${document.id}`}
                                checked={checked}
                                disabled={!ready}
                                onCheckedChange={(value) => handleDocumentToggle(document.id, value === true)}
                              />
                              <span className="min-w-0 flex-1">
                                <span className="block truncate font-medium">{document.fileName || "Untitled document"}</span>
                                <span className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                                  <Badge variant={ready ? "default" : "secondary"} className="text-[10px]">
                                    {ready ? "Ready" : document.processingStatus || "Unknown"}
                                  </Badge>
                                  {document.kgStatus && (
                                    <Badge variant="outline" className="text-[10px]">
                                      KG: {document.kgStatus}
                                    </Badge>
                                  )}
                                </span>
                              </span>
                            </Label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  {hasInProgress && (
                    <p className="text-xs text-muted-foreground">
                      Some documents are still processing. They will become selectable when ready.
                    </p>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="quiz-question-count">Question Count</Label>
                <Input
                  id="quiz-question-count"
                  type="number"
                  min={1}
                  value={questionCount}
                  onChange={(event) => setQuestionCount(event.target.value)}
                />
              </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isGenerating}>
              Cancel
            </Button>
            <Button onClick={handleGenerate} disabled={isGenerating}>
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating
                </>
              ) : (
                "Generate"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
