import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import { ArrowLeft, Eye, Loader2, Play, RefreshCw, Trophy } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { checkStatus, getQuizAttempts, getQuizById } from "../../services/quizService";
import type { QuizAttemptSummary, QuizHistoryItem, QuizStatusResponse } from "../../types/quiz";

export default function QuizDetail() {
  const { quizId } = useParams();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<QuizHistoryItem | null>(null);
  const [status, setStatus] = useState<QuizStatusResponse | null>(null);
  const [attempts, setAttempts] = useState<QuizAttemptSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadQuiz();
  }, [quizId]);

  const loadQuiz = async () => {
    if (!quizId) return;

    setIsLoading(true);
    try {
      const [quizSummary, quizStatus, quizAttempts] = await Promise.all([
        getQuizById(quizId),
        checkStatus(quizId),
        getQuizAttempts(quizId),
      ]);
      setQuiz(quizSummary);
      setStatus(quizStatus);
      setAttempts(quizAttempts);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load quiz.";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (value: string | null) => {
    if (!value) return "Not available";
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  };

  const formatScore = (value: number | null) => {
    if (value === null || value === undefined) return "Not submitted";
    return `${Math.round(value)}%`;
  };

  const isReady = (status?.status ?? quiz?.status)?.toUpperCase() === "READY";

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading quiz
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Button variant="ghost" className="mb-2 px-0" onClick={() => navigate("/quizzes")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Quizzes
          </Button>
          <h1 className="text-3xl mb-2">{quiz?.subjectName || "Quiz"}</h1>
          <p className="text-muted-foreground">Each take creates a new attempt. Completed attempts keep their own review.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadQuiz} disabled={isLoading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button disabled={!isReady} onClick={() => navigate(`/quizzes/${quizId}/take`)}>
            <Play className="mr-2 h-4 w-4" />
            Take Quiz
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Status</CardDescription>
            <CardTitle><Badge>{status?.status || quiz?.status || "Unknown"}</Badge></CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Questions</CardDescription>
            <CardTitle>{status?.questionCount || quiz?.questionCount || 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Attempts</CardDescription>
            <CardTitle>{attempts.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Best Score</CardDescription>
            <CardTitle>{formatScore(quiz?.bestScore ?? null)}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-primary" />
            Attempts
          </CardTitle>
          <CardDescription>Open a completed attempt to review its answers and explanations.</CardDescription>
        </CardHeader>
        <CardContent>
          {attempts.length === 0 ? (
            <div className="py-12 text-center">
              <h3 className="font-semibold">No attempts yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">Take this quiz to create the first attempt.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Attempt</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Finished</TableHead>
                  <TableHead className="text-right">Review</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {attempts.map((attempt) => {
                  const isFinished = Boolean(attempt.finishedAt);
                  return (
                    <TableRow key={attempt.attemptId}>
                      <TableCell className="font-medium">Attempt #{attempt.attemptNumber}</TableCell>
                      <TableCell>{formatScore(attempt.score)}</TableCell>
                      <TableCell>{formatDate(attempt.startedAt)}</TableCell>
                      <TableCell>{formatDate(attempt.finishedAt)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={!isFinished}
                          onClick={() => navigate(`/quizzes/attempts/${attempt.attemptId}/review`)}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          Review
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
