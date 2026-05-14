import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface Vital {
  id: string;
  elder_id: string;
  vital_type: string;
  value: number;
  unit: string;
  recorded_at: string;
  created_at: string;
}

export interface VitalCreate {
  elder_id: string;
  vital_type: string;
  value: number;
  unit: string;
}

const getAuthHeader = (): HeadersInit | undefined => {
  if (typeof window === 'undefined') return undefined;
  const token = localStorage.getItem('access_token');
  if (!token) return undefined;
  return { Authorization: `Bearer ${token}` } as Record<string, string>;
};


export const vitalsService = {
  async getVitals(elderId: string, vitalType?: string): Promise<ApiResponse<Vital[]>> {
    const query = vitalType ? `?vital_type=${vitalType}` : '';
    return apiClient<Vital[]>(
      `${API_BASE_URL}/api/v1/vitals/${elderId}${query}`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async createVital(data: VitalCreate): Promise<ApiResponse<Vital>> {
    return apiClient<Vital>(
      `${API_BASE_URL}/api/v1/vitals`,
      {
        method: 'POST',
        headers: getAuthHeader(),
        body: JSON.stringify(data),
      }
    );
  },
};
