import { apiClient } from "../lib/apiClient";
import type { ReviewScheduleItem } from "../types/studyPlan";

export function getReviewSchedule(): Promise<ReviewScheduleItem[]> {
  return apiClient.get<ReviewScheduleItem[]>("/api/StudyPlan/reviews", { auth: true });
}

export function generateReviewSchedule(): Promise<ReviewScheduleItem[]> {
  return apiClient.post<ReviewScheduleItem[]>("/api/StudyPlan/generate", undefined, { auth: true });
}

export function completeReviewItem(itemId: string): Promise<void> {
  return apiClient.post<void>(`/api/StudyPlan/reviews/${itemId}/complete`, undefined, { auth: true });
}
