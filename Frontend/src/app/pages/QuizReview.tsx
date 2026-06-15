import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { reviewAttempt } from "../../services/quizService";
import type { QuizReviewResponse } from "../../types/quiz";

export default function QuizReview() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState<QuizReviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!attemptId) return;

    let isMounted = true;
    const loadReview = async () => {
      setIsLoading(true);
      try {
        const response = await reviewAttempt(attemptId);
        if (isMounted) setReview(response);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load quiz review.";
        toast.error(message);
        navigate("/quizzes");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadReview();
    return () => {
      isMounted = false;
    };
  }, [attemptId, navigate]);

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading review
      </div>
    );
  }

  if (!review) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl mb-2">Quiz Review</h1>
          <p className="text-muted-foreground">Review your answers and explanations.</p>
        </div>
        <Button variant="outline" onClick={() => navigate("/quizzes")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Quizzes
        </Button>
      </div>

      <Card className="border-2 border-primary/20 bg-primary/5">
        <CardContent className="flex flex-col gap-4 py-8 text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Final Score</p>
            <p className="mt-2 text-5xl font-bold text-primary">{Math.round(review.score)}%</p>
          </div>
          <div>
            <p className="text-2xl font-semibold">{review.correctCount} / {review.totalCount} correct</p>
            <p className="mt-1 text-sm text-muted-foreground">Completed quiz attempt</p>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {(review.questions ?? []).map((question, index) => {
          const selected = question.options?.find((option) => option.label === question.selectedOption);
          const correct = question.options?.find((option) => option.label === question.correctOption);

          return (
            <Card key={question.id} className="border-2">
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <CardTitle className="text-lg leading-relaxed">
                    {index + 1}. {question.questionText || "Untitled question"}
                  </CardTitle>
                  <Badge variant={question.isCorrect ? "default" : "destructive"} className="w-fit">
                    {question.isCorrect ? "Correct" : "Incorrect"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={`rounded-lg border p-4 ${question.isCorrect ? "border-green-500 bg-green-50 text-green-950" : "border-red-500 bg-red-50 text-red-950"}`}>
                  <div className="flex items-start gap-3">
                    {question.isCorrect ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" /> : <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />}
                    <div>
                      <p className="font-medium">Your answer</p>
                      <p>{selected ? `${selected.label}. ${selected.text}` : "No answer selected"}</p>
                    </div>
                  </div>
                </div>

                {!question.isCorrect && (
                  <div className="rounded-lg border border-green-500 bg-green-50 p-4 text-green-950">
                    <p className="font-medium">Correct answer</p>
                    <p>{correct ? `${correct.label}. ${correct.text}` : question.correctOption}</p>
                  </div>
                )}

                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="font-medium">Explanation</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{question.explanation || "No explanation provided."}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {question.concept && <Badge variant="secondary">Concept: {question.concept}</Badge>}
                  {question.bloomLevel && <Badge variant="outline">{question.bloomLevel}</Badge>}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
