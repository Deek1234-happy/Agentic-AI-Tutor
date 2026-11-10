import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Progress as ProgressBar } from "../components/ui/progress";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Button } from "../components/ui/button";
import { Award, BookOpenCheck, CalendarClock, Check, RotateCcw } from "lucide-react";
import { getUserProgress } from "../../services/analyticsService";
import {
  completeReviewItem,
  generateReviewSchedule,
  getReviewSchedule,
} from "../../services/studyPlanService";
import type { ProgressDashboardResponse } from "../../types/analytics";
import type { ReviewScheduleItem } from "../../types/studyPlan";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const emptyProgress: ProgressDashboardResponse = {
  totalQuizzes: 0,
  activeSubjects: 0,
  overallMastery: 0,
  monthlyPerformance: [],
  subjectProgress: [],
  weakConcepts: [],
};

export default function Progress() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState<ProgressDashboardResponse>(emptyProgress);
  const [isLoading, setIsLoading] = useState(true);
  const [reviewSchedule, setReviewSchedule] = useState<ReviewScheduleItem[]>([]);
  const [isScheduleLoading, setIsScheduleLoading] = useState(true);
  const [isGeneratingSchedule, setIsGeneratingSchedule] = useState(false);
  const [completingReviewId, setCompletingReviewId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadProgress() {
      setIsLoading(true);
      try {
        const data = await getUserProgress();
        if (isMounted) setProgress(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load progress analytics.";
        if (isMounted) setProgress(emptyProgress);
        toast.error(message);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadProgress();
    getReviewSchedule()
      .then((items) => {
        if (isMounted) setReviewSchedule(items);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Unable to load your revision schedule.";
        if (isMounted) toast.error(message);
      })
      .finally(() => {
        if (isMounted) setIsScheduleLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const overallPerformance = progress.monthlyPerformance ?? [];
  const subjectProgress = progress.subjectProgress ?? [];
  const weakConcepts = progress.weakConcepts ?? [];
  const avgMastery = progress.overallMastery ?? 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dueReviews = reviewSchedule.filter((item) =>
    !item.completed &&
    (!item.scheduledDate || new Date(`${item.scheduledDate.slice(0, 10)}T00:00:00`) <= today)
  );
  const upcomingReviews = reviewSchedule.filter((item) =>
    !item.completed &&
    item.scheduledDate &&
    new Date(`${item.scheduledDate.slice(0, 10)}T00:00:00`) > today
  );
  const completedReviews = reviewSchedule.filter((item) => item.completed);

  const handleGenerateSchedule = async () => {
    setIsGeneratingSchedule(true);
    try {
      const items = await generateReviewSchedule();
      setReviewSchedule(items);
      toast.success(items.length > 0 ? "Revision schedule is ready." : "No weak topics are ready to schedule yet.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to create your revision schedule.";
      toast.error(message);
    } finally {
      setIsGeneratingSchedule(false);
    }
  };

  const handleCompleteReview = async (itemId: string) => {
    setCompletingReviewId(itemId);
    try {
      await completeReviewItem(itemId);
      setReviewSchedule((items) =>
        items.map((item) => item.id === itemId ? { ...item, completed: true, status: "Reviewed" } : item)
      );
      toast.success("Review marked complete.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to update this review.";
      toast.error(message);
    } finally {
      setCompletingReviewId(null);
    }
  };

  const openTopicPractice = (topic: (typeof weakConcepts)[number]) => {
    const params = new URLSearchParams({
      focusConcept: topic.conceptName || "",
      subjectId: topic.subjectId,
      documentIds: topic.sourceDocumentIds.join(","),
      sourceChunkIds: topic.sourceChunkIds.join(","),
    });
    navigate(`/quizzes?${params.toString()}`);
  };

  const findPracticeTopic = (item: ReviewScheduleItem) =>
    weakConcepts.find((topic) =>
      topic.subjectId === item.subjectId &&
      topic.conceptName?.trim().toLowerCase() === item.conceptName.trim().toLowerCase()
    );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl mb-2">Progress & Analytics</h1>
          <p className="text-muted-foreground">Track your learning journey and achievements</p>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Overall Mastery</p>
                {isLoading ? <Skeleton className="h-9 w-20" /> : <p className="text-3xl">{avgMastery}%</p>}
                <div className="flex items-center gap-1 text-sm text-green-600 mt-2">
                  <Award className="w-4 h-4" />
                  <span>Based on completed quizzes</span>
                </div>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <Award className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Quizzes Completed</p>
              {isLoading ? <Skeleton className="h-9 w-16 mb-2" /> : <p className="text-3xl mb-2">{progress.totalQuizzes}</p>}
              <ProgressBar value={Math.min(progress.totalQuizzes, 100)} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Active Subjects</p>
              {isLoading ? <Skeleton className="h-9 w-16 mb-2" /> : <p className="text-3xl mb-2">{progress.activeSubjects}</p>}
              <ProgressBar value={progress.activeSubjects > 0 ? 100 : 0} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <CalendarClock className="h-5 w-5 text-primary" />
                Revision Schedule
              </CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Quiz results set the next review: low scores in 1 day, developing scores in 3 days, and strong scores in 14 days.
              </p>
            </div>
            {weakConcepts.length > 0 && (
              <Button
                variant="outline"
                onClick={handleGenerateSchedule}
                disabled={isGeneratingSchedule}
              >
                {isGeneratingSchedule ? "Creating schedule..." : "Add weak topics"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isScheduleLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : reviewSchedule.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Complete a quiz or add your weak topics to start a personalized revision schedule.
            </p>
          ) : (
            <div className="space-y-6">
              {[
                { title: "Due for review", items: dueReviews, canPractice: true },
                { title: "Coming up", items: upcomingReviews, canPractice: false },
                { title: "Completed", items: completedReviews, canPractice: false },
              ].map(({ title, items, canPractice }) => (
                items.length > 0 && (
                  <section key={title}>
                    <h3 className="mb-3 text-sm font-semibold">{title}</h3>
                    <div className="space-y-2">
                      {items.map((item) => {
                        const practiceTopic = canPractice ? findPracticeTopic(item) : undefined;
                        const hasPracticeSources = Boolean(
                          practiceTopic?.sourceDocumentIds?.length && practiceTopic.sourceChunkIds?.length
                        );

                        return (
                          <div
                            key={item.id}
                            className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="font-medium">{item.conceptName}</h4>
                                <Badge variant={item.completed ? "secondary" : item.accuracy !== null && item.accuracy < 70 ? "destructive" : "outline"}>
                                  {item.status}{item.accuracy !== null ? ` · ${item.accuracy}%` : ""}
                                </Badge>
                              </div>
                              <p className="mt-1 text-sm text-muted-foreground">
                                {item.subjectName} · {item.scheduledDate
                                  ? `Scheduled ${new Date(`${item.scheduledDate.slice(0, 10)}T00:00:00`).toLocaleDateString()}`
                                  : "Due now"} · {item.estimatedMinutes} min
                              </p>
                            </div>
                            {!item.completed && (
                              <div className="flex flex-wrap gap-2">
                                {canPractice && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={!hasPracticeSources}
                                    onClick={() => practiceTopic && openTopicPractice(practiceTopic)}
                                    title={hasPracticeSources
                                      ? "Start a focused quiz. Your results will update the next review date."
                                      : "Source material for focused practice is unavailable."}
                                  >
                                    <RotateCcw className="mr-2 h-4 w-4" />
                                    Practice now
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleCompleteReview(item.id)}
                                  disabled={completingReviewId === item.id}
                                >
                                  <Check className="mr-2 h-4 w-4" />
                                  {completingReviewId === item.id ? "Saving..." : "Mark reviewed"}
                                </Button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpenCheck className="h-5 w-5 text-primary" />
            Topics to Review
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-24 w-full" />
              ))}
            </div>
          ) : weakConcepts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No missed concepts to review yet. Complete a quiz to get topic-specific feedback.
            </p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {weakConcepts.map((topic) => {
                const hasPracticeSources =
                  topic.sourceDocumentIds?.length > 0 && topic.sourceChunkIds?.length > 0;

                return (
                  <div
                    key={`${topic.subjectId}-${topic.conceptName}`}
                    className="rounded-lg border p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="font-medium">{topic.conceptName || "Unnamed concept"}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {topic.subjectName} · {topic.errorCount} missed of {topic.questionCount}
                        </p>
                      </div>
                      <Badge variant={topic.accuracy >= 70 ? "secondary" : "destructive"}>
                        {topic.accuracy}% accuracy
                      </Badge>
                    </div>
                    <ProgressBar value={topic.accuracy} className="mt-3 h-2" />
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!topic.reviewAttemptId}
                        onClick={() =>
                          topic.reviewAttemptId &&
                          navigate(`/quizzes/attempts/${topic.reviewAttemptId}/review`)
                        }
                      >
                        <BookOpenCheck className="mr-2 h-4 w-4" />
                        Review mistakes
                      </Button>
                      <Button
                        size="sm"
                        disabled={!hasPracticeSources}
                        onClick={() => openTopicPractice(topic)}
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Practice this topic
                      </Button>
                    </div>
                    {!hasPracticeSources && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Topic practice is unavailable because its source material is missing.
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Overall Performance Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Overall Performance Trend</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[300px] w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={overallPerformance}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#2563eb"
                  strokeWidth={3}
                  dot={{ fill: "#2563eb", r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Subject Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Progress by Subject</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-6">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="space-y-2">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-3 w-full" />
                </div>
              ))}
            </div>
          ) : subjectProgress.length === 0 ? (
            <p className="text-sm text-muted-foreground">No subject progress is available yet.</p>
          ) : (
            <div className="space-y-6">
            {subjectProgress.map((subject, index) => (
              <div key={index}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h4 className="font-medium">{subject.subject || "Untitled subject"}</h4>
                      <Badge
                        variant={
                          subject.mastery >= 80
                            ? "default"
                            : subject.mastery >= 60
                            ? "secondary"
                            : "destructive"
                        }
                      >
                        {subject.mastery}%
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                      <span>{subject.quizzes} quizzes</span>
                    </div>
                  </div>
                </div>
                <ProgressBar value={subject.mastery} className="h-3" />
              </div>
            ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
