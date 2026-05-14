import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface BackendAlert {
  id: string;
  user_id: string;
  vital_id: string;
  alert_type: string;
  severity: string;
  message: string;
  created_at: string;
  is_resolved: boolean;
}

const getAuthHeader = (): HeadersInit | undefined => {
  if (typeof window === 'undefined') return undefined;
  const token = localStorage.getItem('access_token');
  if (!token) return undefined;
  return { Authorization: `Bearer ${token}` } as Record<string, string>;
};



export const alertsService = {
  async getAlerts(): Promise<ApiResponse<BackendAlert[]>> {
    return apiClient<BackendAlert[]>(
      `${API_BASE_URL}/api/v1/alerts/alerts/me`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async getMyAlerts(): Promise<ApiResponse<BackendAlert[]>> {
    return apiClient<BackendAlert[]>(
      `${API_BASE_URL}/api/v1/alerts/alerts/me`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async getActiveAlerts(): Promise<ApiResponse<BackendAlert[]>> {
    return apiClient<BackendAlert[]>(
      `${API_BASE_URL}/api/v1/alerts/alerts/events/active`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async resolveMyAlert(alertId: string): Promise<ApiResponse<BackendAlert>> {
    return apiClient<BackendAlert>(
      `${API_BASE_URL}/api/v1/alerts/alerts/${alertId}/resolve`,
      {
        method: 'PATCH',
        headers: getAuthHeader(),
      }
    );
  },
};
