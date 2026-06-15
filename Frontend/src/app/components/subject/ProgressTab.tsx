import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Trophy, FileText, Calendar, TrendingUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const quizHistory = [
  {
    id: "quiz-1",
    score: 85,
    totalQuestions: 10,
    date: "2024-03-01",
    documents: ["Differential Equations.pdf", "Integration Techniques.pdf"],
  },
  {
    id: "quiz-2",
    score: 92,
    totalQuestions: 8,
    date: "2024-02-28",
    documents: ["Vector Calculus Notes.pdf"],
  },
  {
    id: "quiz-3",
    score: 78,
    totalQuestions: 12,
    date: "2024-02-25",
    documents: ["Differential Equations.pdf"],
  },
  {
    id: "quiz-4",
    score: 88,
    totalQuestions: 10,
    date: "2024-02-22",
    documents: ["Integration Techniques.pdf", "Vector Calculus Notes.pdf"],
  },
  {
    id: "quiz-5",
    score: 95,
    totalQuestions: 15,
    date: "2024-02-18",
    documents: ["Differential Equations.pdf", "Integration Techniques.pdf", "Vector Calculus Notes.pdf"],
  },
  {
    id: "quiz-6",
    score: 73,
    totalQuestions: 10,
    date: "2024-02-15",
    documents: ["Vector Calculus Notes.pdf"],
  },
];

export default function ProgressTab() {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  };

  const getScoreBadgeVariant = (percentage: number) => {
    if (percentage >= 90) return "default";
    if (percentage >= 70) return "secondary";
    return "destructive";
  };

  // Prepare chart data from quiz history (sorted by date, oldest first)
  const chartData = [...quizHistory]
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .map((quiz, index) => ({
      attempt: index + 1,
      score: Math.round((quiz.score / quiz.totalQuestions) * 100),
      date: formatDate(quiz.date),
    }));

  return (
    <div className="space-y-6">
      {/* Progress Over Time Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Progress Over Quizzes
          </CardTitle>
        </CardHeader>
        <CardContent>
          {quizHistory.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No quiz data available yet.</p>
              <p className="text-sm mt-1">Complete quizzes to see your progress trend.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="attempt" 
                  label={{ value: 'Quiz Attempt', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  domain={[0, 100]} 
                  label={{ value: 'Score (%)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
                          <p className="font-semibold">Attempt {payload[0].payload.attempt}</p>
                          <p className="text-sm text-muted-foreground">{payload[0].payload.date}</p>
                          <p className="text-primary font-bold">{payload[0].value}%</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#2563eb"
                  strokeWidth={3}
                  dot={{ fill: "#2563eb", r: 5 }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Quiz History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-primary" />
            Quiz History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {quizHistory.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Trophy className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No quizzes taken yet for this subject.</p>
              <p className="text-sm mt-1">Complete a quiz to see your progress here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {quizHistory.map((quiz) => {
                const percentage = Math.round((quiz.score / quiz.totalQuestions) * 100);
                return (
                  <div
                    key={quiz.id}
                    className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-3">
                          <Badge variant={getScoreBadgeVariant(percentage)} className="text-lg px-3 py-1">
                            {percentage}%
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {quiz.score} / {quiz.totalQuestions} correct
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="w-4 h-4" />
                          <span>{formatDate(quiz.date)}</span>
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <FileText className="w-4 h-4" />
                            <span className="font-medium">Documents used:</span>
                          </div>
                          <div className="flex flex-wrap gap-2 ml-6">
                            {quiz.documents.map((doc, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">
                                {doc}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}