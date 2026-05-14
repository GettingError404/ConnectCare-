import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
  role?: string;
  roles?: string[];
}

export interface UserProfileResponse extends UserResponse {
  role?: string;
  roles: string[];
}

export const authService = {
  async login(data: LoginRequest): Promise<ApiResponse<TokenPair>> {
    return apiClient<TokenPair>(`${API_BASE_URL}/api/v1/auth/auth/login`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async register(data: RegisterRequest): Promise<ApiResponse<UserResponse>> {
    return apiClient<UserResponse>(`${API_BASE_URL}/api/v1/auth/auth/register`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async refresh(refreshToken: string): Promise<ApiResponse<TokenPair>> {
    return apiClient<TokenPair>(`${API_BASE_URL}/api/v1/auth/auth/refresh`, {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async logout(refreshToken: string): Promise<ApiResponse<null>> {
    return apiClient<null>(`${API_BASE_URL}/api/v1/auth/auth/logout`, {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async getCurrentUser(): Promise<ApiResponse<UserProfileResponse>> {
    return apiClient<UserProfileResponse>(`${API_BASE_URL}/api/v1/auth/auth/me`, {
      method: 'GET',
    });
  },
};

