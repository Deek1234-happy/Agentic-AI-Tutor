export type QuizStatus = "GENERATING" | "READY" | "FAILED" | string;

export interface QuizInitiateRequest {
  subjectId: string;
  documentIds: string[];
  numberOfQuestions: number;
}

export interface QuizInitiateResponse {
  quizId: string;
  status: QuizStatus | null;
  message: string | null;
}

export interface QuizStatusResponse {
  quizId: string;
  status: QuizStatus | null;
  questionCount: number;
  generatedAt: string | null;
}

export interface QuizOptionDto {
  label: string;
  text: string | null;
}

export interface QuizQuestionDto {
  id: string;
  slotIndex: number;
  questionText: string | null;
  bloomLevel: string | null;
  concept: string | null;
  options: QuizOptionDto[] | null;
}

export interface QuizStartResponse {
  quizId: string;
  attemptId: string;
  attemptNumber: number;
  questions: QuizQuestionDto[] | null;
}

export interface QuizAnswerItem {
  questionId: string;
  selectedOption: string;
}

export interface QuizSubmitRequest {
  attemptId: string;
  answers: QuizAnswerItem[];
}

export interface QuizSubmitResponse {
  attemptId: string;
  score: number;
  correctCount: number;
  totalCount: number;
  finishedAt: string;
}

export interface QuizAttemptSummary {
  attemptId: string;
  attemptNumber: number;
  score: number | null;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface QuizHistoryItem {
  quizId: string;
  status: QuizStatus | null;
  subjectId: string | null;
  subjectName: string | null;
  questionCount: number;
  createdAt: string | null;
  attemptCount: number;
  bestScore: number | null;
}

export interface QuizHistoryQuery {
  subjectId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

export interface QuizReviewQuestionDto {
  id: string;
  questionText: string | null;
  explanation: string | null;
  bloomLevel: string | null;
  concept: string | null;
  correctOption: string;
  selectedOption: string | null;
  isCorrect: boolean;
  options: QuizOptionDto[] | null;
}

export interface QuizReviewResponse {
  attemptId: string;
  quizId: string;
  score: number;
  correctCount: number;
  totalCount: number;
  startedAt: string | null;
  finishedAt: string | null;
  questions: QuizReviewQuestionDto[] | null;
}
