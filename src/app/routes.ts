import { createBrowserRouter } from "react-router";
import Welcome from "./pages/Welcome";
import MainLayout from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";
import Subjects from "./pages/Subjects";
import SubjectDetail from "./pages/SubjectDetail";
import Chat from "./pages/Chat";
import Quiz from "./pages/Quiz";
import QuizDetail from "./pages/QuizDetail";
import ActiveQuiz from "./pages/ActiveQuiz";
import QuizReview from "./pages/QuizReview";
import Progress from "./pages/Progress";
import Settings from "./pages/Settings";
import Notifications from "./pages/Notifications";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import ProtectedRoute from "./components/ProtectedRoute";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Welcome,
  },
  {
    path: "/login",
    Component: Welcome,
  },
  {
    path: "/forgot-password",
    Component: ForgotPassword,
  },
  {
    path: "/reset-password",
    Component: ResetPassword,
  },
  {
    // All /dashboard/* routes require authentication
    Component: ProtectedRoute,
    children: [
      {
        path: "/dashboard",
        Component: MainLayout,
        children: [
          { index: true, Component: Dashboard },
          { path: "subjects", Component: Subjects },
          { path: "subjects/:subjectId", Component: SubjectDetail },
          { path: "chat", Component: Chat },
          { path: "quiz", Component: Quiz },
          { path: "quiz/:quizId", Component: QuizDetail },
          { path: "quiz/:quizId/take", Component: ActiveQuiz },
          { path: "quiz/attempts/:attemptId/review", Component: QuizReview },
          { path: "progress", Component: Progress },
          { path: "settings", Component: Settings },
          { path: "notifications", Component: Notifications },
        ],
      },
      {
        path: "/quizzes",
        Component: MainLayout,
        children: [
          { index: true, Component: Quiz },
          { path: ":quizId", Component: QuizDetail },
          { path: ":quizId/take", Component: ActiveQuiz },
          { path: "attempts/:attemptId/review", Component: QuizReview },
        ],
      },
    ],
  },
]);
