import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface CurrentUserProfileResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
  role?: string;
  roles?: string[];
}

export const profileService = {
  async getCurrentUser(): Promise<ApiResponse<CurrentUserProfileResponse>> {
    return apiClient<CurrentUserProfileResponse>(`${API_BASE_URL}/api/v1/auth/auth/me`, {
      method: 'GET',
    });
  },
};