import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Progress as ProgressBar } from "../components/ui/progress";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Award, Trophy } from "lucide-react";
import { getUserProgress } from "../../services/analyticsService";
import type { ProgressDashboardResponse } from "../../types/analytics";
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
  const [progress, setProgress] = useState<ProgressDashboardResponse>(emptyProgress);
  const [isLoading, setIsLoading] = useState(true);

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
    return () => {
      isMounted = false;
    };
  }, []);

  const overallPerformance = progress.monthlyPerformance ?? [];
  const subjectProgress = progress.subjectProgress ?? [];
  const avgMastery = progress.overallMastery ?? 0;

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
