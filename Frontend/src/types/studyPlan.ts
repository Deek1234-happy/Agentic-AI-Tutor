export interface ReviewScheduleItem {
  id: string;
  subjectId: string;
  subjectName: string;
  conceptName: string;
  scheduledDate: string | null;
  estimatedMinutes: number;
  accuracy: number | null;
  status: string;
  completed: boolean;
}
