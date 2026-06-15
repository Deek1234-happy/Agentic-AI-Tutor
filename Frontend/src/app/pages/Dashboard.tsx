import { useEffect, useState } from "react";
import { Link } from "react-router";
import { toast } from "sonner";
import { BookOpen, FileText, MessageSquare, TrendingUp, Trophy } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Progress as ProgressBar } from "../components/ui/progress";
import { Skeleton } from "../components/ui/skeleton";
import { useUserProfile } from "../../hooks/useUserProfile";
import { getUserProgress } from "../../services/analyticsService";
import type { SubjectProgressDto } from "../../types/analytics";

const quickActions = [
  {
    title: "Chat with AI Tutor",
    description: "Ask questions about your study materials",
    icon: MessageSquare,
    link: "/dashboard/chat",
    color: "bg-blue-50 text-blue-600 hover:bg-blue-100",
  },
  {
    title: "Take a Quiz",
    description: "Test your knowledge with AI-generated quizzes",
    icon: Trophy,
    link: "/quizzes",
    color: "bg-purple-50 text-purple-600 hover:bg-purple-100",
  },
  {
    title: "View Progress",
    description: "Track your learning analytics and trends",
    icon: TrendingUp,
    link: "/dashboard/progress",
    color: "bg-green-50 text-green-600 hover:bg-green-100",
  },
];

function StatCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-8 w-16 mt-2" />
          </div>
          <Skeleton className="w-12 h-12 rounded-xl" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: profile, isLoading } = useUserProfile();
  const [subjectProgress, setSubjectProgress] = useState<SubjectProgressDto[]>([]);
  const [isProgressLoading, setIsProgressLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadProgress() {
      setIsProgressLoading(true);
      try {
        const progress = await getUserProgress();
        if (isMounted) setSubjectProgress(progress.subjectProgress ?? []);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load subject progress.";
        toast.error(message);
        if (isMounted) setSubjectProgress([]);
      } finally {
        if (isMounted) setIsProgressLoading(false);
      }
    }

    loadProgress();
    return () => {
      isMounted = false;
    };
  }, []);

  const stats = [
    {
      name: "Total Subjects",
      value: profile?.numberOfSubjects ?? 0,
      icon: BookOpen,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      name: "Uploaded Files",
      value: profile?.numberOfDocuments ?? 0,
      icon: FileText,
      color: "text-purple-600",
      bg: "bg-purple-50",
    },
    {
      name: "Quizzes Taken",
      value: profile?.numberOfQuizzes ?? 0,
      icon: Trophy,
      color: "text-green-600",
      bg: "bg-green-50",
    },
  ];

  const firstName = profile?.firstName ?? "";
  const greeting = firstName ? `Welcome back, ${firstName}!` : "Welcome back!";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Dashboard</h1>
          {isLoading ? (
            <Skeleton className="h-5 w-64 mt-2" />
          ) : (
            <p className="text-sm text-muted-foreground mt-1">
              {greeting} Here&apos;s your learning overview.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild className="rounded-full">
            <Link to="/dashboard/subjects">View subjects</Link>
          </Button>
          <Button size="sm" asChild className="rounded-full shadow-sm hover:shadow transition-all duration-200">
            <Link to="/dashboard/chat">
              <MessageSquare className="w-4 h-4 mr-2" />
              Open AI Tutor
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => <StatCardSkeleton key={i} />)
          : stats.map((stat) => (
              <Card
                key={stat.name}
                className="border bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/40 shadow-sm"
              >
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.name}</p>
                      <p className="text-2xl font-semibold mt-2 tracking-tight">{stat.value}</p>
                    </div>
                    <div className={`p-3 rounded-2xl ${stat.bg} ${stat.color}`}>
                      <stat.icon className="w-5 h-5" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      <Card className="border bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/40 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="w-4 h-4 text-primary" />
            Progress by Subject
          </CardTitle>
          <Button variant="outline" size="sm" asChild className="rounded-full">
            <Link to="/dashboard/progress">View analytics</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {isProgressLoading ? (
            <div className="space-y-5">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="space-y-2">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-3 w-full" />
                </div>
              ))}
            </div>
          ) : subjectProgress.length === 0 ? (
            <p className="text-sm text-muted-foreground">No subject progress is available yet.</p>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              {subjectProgress.map((subject, index) => (
                <div key={`${subject.subject ?? "subject"}-${index}`} className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="font-medium truncate">{subject.subject || "Untitled subject"}</h3>
                      <p className="text-sm text-muted-foreground">{subject.quizzes} quizzes</p>
                    </div>
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
                  <ProgressBar value={subject.mastery} className="h-3" />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-tight text-muted-foreground uppercase">
            Quick actions
          </h2>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickActions.map((action) => (
            <Link key={action.title} to={action.link} className="group">
              <Card className="h-full border bg-card hover:bg-accent/30 transition-all duration-200 shadow-sm hover:shadow">
                <CardContent className="p-5">
                  <div
                    className={`w-10 h-10 rounded-2xl flex items-center justify-center mb-4 ${action.color} transition-colors`}
                  >
                    <action.icon className="w-5 h-5" />
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="font-medium tracking-tight truncate">{action.title}</h3>
                      <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                        {action.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
