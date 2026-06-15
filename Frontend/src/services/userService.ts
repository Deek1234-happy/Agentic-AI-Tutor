/**
 * User service — calls the /api/User endpoints defined in swagger.json.
 *
 *  GET /api/User/profile  → UserResponse  (Bearer required)
 *  PUT /api/User/profile  → UserResponse  (Bearer required)
 */

import { apiClient } from "../lib/apiClient";
import type { UserProfileResponse, UpdateProfileRequest } from "../types/user";

/** Fetch the authenticated user's full profile including dashboard stats */
export async function getUserProfile(): Promise<UserProfileResponse> {
  return apiClient.get<UserProfileResponse>("/api/User/profile", { auth: true });
}

/** Update the authenticated user's profile fields */
export async function updateUserProfile(payload: UpdateProfileRequest): Promise<UserProfileResponse> {
  return apiClient.put<UserProfileResponse>("/api/User/profile", payload, { auth: true });
}
