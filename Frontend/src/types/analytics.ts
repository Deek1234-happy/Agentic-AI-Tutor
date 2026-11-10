export interface MonthlyPerformanceDto {
  month: string | null;
  score: number;
}

export interface SubjectProgressDto {
  subject: string | null;
  mastery: number;
  quizzes: number;
  studyTime: string | null;
}

export interface ConceptMasteryDto {
  conceptName: string | null;
  errorCount: number;
  correctCount: number;
  questionCount: number;
  accuracy: number;
  subjectId: string;
  subjectName: string;
  reviewAttemptId: string | null;
  sourceDocumentIds: string[];
  sourceChunkIds: string[];
}

export interface ProgressDashboardResponse {
  totalQuizzes: number;
  activeSubjects: number;
  overallMastery: number;
  monthlyPerformance: MonthlyPerformanceDto[] | null;
  subjectProgress: SubjectProgressDto[] | null;
  weakConcepts: ConceptMasteryDto[] | null;
}
