import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Loader2, Send, Trophy } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { startAttempt, submitQuiz } from "../../services/quizService";
import type { QuizQuestionDto, QuizStartResponse } from "../../types/quiz";

export default function ActiveQuiz() {
  const { quizId } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState<QuizStartResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const questions = useMemo(() => attempt?.questions ?? [], [attempt]);
  const currentQuestion = questions[currentIndex] as QuizQuestionDto | undefined;
  const answeredCount = Object.keys(answers).length;

  useEffect(() => {
    if (!quizId) return;

    let isMounted = true;
    const loadAttempt = async () => {
      setIsLoading(true);
      try {
        const response = await startAttempt(quizId);
        if (isMounted) setAttempt(response);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to start quiz.";
        toast.error(message);
        navigate(quizId ? `/quizzes/${quizId}` : "/quizzes");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadAttempt();
    return () => {
      isMounted = false;
    };
  }, [quizId, navigate]);

  const handleSelect = (questionId: string, selectedOption: string) => {
    setAnswers((previous) => ({ ...previous, [questionId]: selectedOption }));
  };

  const handleSubmit = async () => {
    if (!quizId || !attempt) return;

    if (answeredCount !== questions.length) {
      toast.error("Please answer every question before submitting.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await submitQuiz(quizId, {
        attemptId: attempt.attemptId,
        answers: questions.map((question) => ({
          questionId: question.id,
          selectedOption: answers[question.id],
        })),
      });

      toast.success(`Exam submitted. Score: ${Math.round(response.score)}%`);
      navigate(`/quizzes/attempts/${response.attemptId}/review`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to submit quiz.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Starting quiz
      </div>
    );
  }

  if (!currentQuestion || questions.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <h2 className="text-xl font-semibold">No questions available</h2>
          <p className="mt-2 text-muted-foreground">This quiz does not have any generated questions yet.</p>
          <Button className="mt-6" onClick={() => navigate(`/quizzes/${quizId}`)}>Back to Quiz</Button>
        </CardContent>
      </Card>
    );
  }

  const progress = ((currentIndex + 1) / questions.length) * 100;
  const isFinalQuestion = currentIndex === questions.length - 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl mb-2">Active Quiz</h1>
          <p className="text-muted-foreground">Attempt #{attempt?.attemptNumber} · {answeredCount} of {questions.length} answered</p>
        </div>
        <Button variant="outline" onClick={() => navigate(`/quizzes/${quizId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Exit
        </Button>
      </div>

      <Card className="border-2">
        <CardHeader className="border-b">
          <div className="flex items-center justify-between gap-4">
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5 text-primary" />
              Question {currentIndex + 1} of {questions.length}
            </CardTitle>
            {currentQuestion.bloomLevel && <Badge variant="outline">{currentQuestion.bloomLevel}</Badge>}
          </div>
          <Progress value={progress} className="mt-4 h-2" />
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <div>
            {currentQuestion.concept && (
              <p className="mb-3 text-sm font-medium text-primary">{currentQuestion.concept}</p>
            )}
            <h2 className="text-xl font-semibold leading-relaxed">{currentQuestion.questionText || "Untitled question"}</h2>
          </div>

          <div role="radiogroup" aria-label="Answer options" className="grid gap-3">
            {(currentQuestion.options ?? []).map((option) => {
              const isSelected = answers[currentQuestion.id] === option.label;

              return (
                <button
                  key={option.label}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => handleSelect(currentQuestion.id, option.label)}
                  className={`flex w-full cursor-pointer items-center gap-3 rounded-lg border-2 p-4 text-left transition-all ${
                    isSelected
                      ? "border-primary bg-primary/10 shadow-sm ring-2 ring-primary/20"
                      : "border-border hover:border-primary/40 hover:bg-accent"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border text-sm font-semibold ${
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-background text-muted-foreground"
                    }`}
                  >
                    {option.label}
                  </span>
                  <span className="flex-1">
                    <span className="font-medium">{option.label}.</span> {option.text}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="flex justify-between border-t pt-4">
            <Button variant="outline" onClick={() => setCurrentIndex((value) => value - 1)} disabled={currentIndex === 0}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            {isFinalQuestion ? (
              <Button onClick={handleSubmit} disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Submitting
                  </>
                ) : (
                  <>
                    <Send className="mr-2 h-4 w-4" />
                    Submit Exam
                  </>
                )}
              </Button>
            ) : (
              <Button onClick={() => setCurrentIndex((value) => value + 1)}>
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
