import { apiClient } from "../lib/apiClient";
import type { ProgressDashboardResponse } from "../types/analytics";

export function getUserProgress(): Promise<ProgressDashboardResponse> {
  return apiClient.get<ProgressDashboardResponse>("/api/Analytics/progress", { auth: true });
}
