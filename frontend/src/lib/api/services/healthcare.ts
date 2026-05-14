import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface ElderResponse {
  id: string;
  email: string;
  full_name: string;
  age: number;
  conditions: string[];
  emergency_contacts: unknown[];
  created_at: string;
}

export interface ElderCreate {
  email: string;
  full_name: string;
  age: number;
  conditions?: string[];
}

export interface ElderUpdate {
  full_name?: string;
  age?: number;
  conditions?: string[];
}

const getAuthHeader = (): HeadersInit | undefined => {
  if (typeof window === 'undefined') return undefined;
  const token = localStorage.getItem('access_token');
  if (!token) return undefined;
  return { Authorization: `Bearer ${token}` } as Record<string, string>;
};


export const healthcareService = {
  async getElder(elderId: string): Promise<ApiResponse<ElderResponse>> {
    return apiClient<ElderResponse>(
      `${API_BASE_URL}/api/v1/healthcare/api/v1/healthcare/elders/${elderId}`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async getMedicalProfile(elderId: string): Promise<ApiResponse<unknown>> {
    return apiClient<unknown>(
      `${API_BASE_URL}/api/v1/healthcare/api/v1/healthcare/elders/${elderId}/medical-profile`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async createElder(data: ElderCreate): Promise<ApiResponse<ElderResponse>> {
    return apiClient<ElderResponse>(
      `${API_BASE_URL}/api/v1/healthcare/api/v1/healthcare/elders`,
      {
        method: 'POST',
        headers: getAuthHeader(),
        body: JSON.stringify(data),
      }
    );
  },

  async updateElder(elderId: string, data: ElderUpdate): Promise<ApiResponse<ElderResponse>> {
    return apiClient<ElderResponse>(
      `${API_BASE_URL}/api/v1/healthcare/api/v1/healthcare/elders/${elderId}`,
      {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify(data),
      }
    );
  },
};
