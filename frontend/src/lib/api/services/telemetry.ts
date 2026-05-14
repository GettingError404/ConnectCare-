import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface TelemetryReading {
  id: string;
  recorded_at: string;
  heart_rate?: number | null;
  spo2?: number | null;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  respiratory_rate?: number | null;
  glucose_level?: number | null;
  body_temperature?: number | null;
  battery_level?: number | null;
  signal_strength?: number | null;
  fall_detected?: boolean | null;
}

const getAuthHeader = (): HeadersInit | undefined => {
  if (typeof window === 'undefined') return undefined;
  const token = localStorage.getItem('access_token');
  if (!token) return undefined;
  return { Authorization: `Bearer ${token}` } as Record<string, string>;
};

export const telemetryService = {
  async getLatestTelemetry(elderId: string, limit = 50): Promise<ApiResponse<TelemetryReading[]>> {
    return apiClient<TelemetryReading[]>(
      `${API_BASE_URL}/api/v1/telemetry/api/v1/telemetry/elders/${elderId}/latest?limit=${limit}`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async getTelemetryTimeline(elderId: string, limit = 100): Promise<ApiResponse<TelemetryReading[]>> {
    return apiClient<TelemetryReading[]>(
      `${API_BASE_URL}/api/v1/telemetry/api/v1/telemetry/elders/${elderId}/timeline?limit=${limit}`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },
};