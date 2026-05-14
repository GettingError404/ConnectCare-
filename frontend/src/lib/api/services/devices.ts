import { apiClient } from '../client';
import type { ApiResponse } from '../types';
import { API_BASE_URL } from '../config';

export interface Device {
  id: string;
  name: string;
  type: string;
  status: string;
  last_reading?: unknown;
  created_at: string;
}

export interface DeviceCreate {
  name: string;
  type: string;
}

const getAuthHeader = (): HeadersInit | undefined => {
  if (typeof window === 'undefined') return undefined;
  const token = localStorage.getItem('access_token');
  if (!token) return undefined;
  return { Authorization: `Bearer ${token}` } as Record<string, string>;
};


export const devicesService = {
  async getMyDevices(): Promise<ApiResponse<Device[]>> {
    return apiClient<Device[]>(
      `${API_BASE_URL}/api/v1/devices/me`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async getDevices(): Promise<ApiResponse<Device[]>> {
    return apiClient<Device[]>(
      `${API_BASE_URL}/api/v1/devices`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async getDevice(deviceId: string): Promise<ApiResponse<Device>> {
    return apiClient<Device>(
      `${API_BASE_URL}/api/v1/devices/${deviceId}`,
      {
        method: 'GET',
        headers: getAuthHeader(),
      }
    );
  },

  async createDevice(data: DeviceCreate): Promise<ApiResponse<Device>> {
    return apiClient<Device>(
      `${API_BASE_URL}/api/v1/devices`,
      {
        method: 'POST',
        headers: getAuthHeader(),
        body: JSON.stringify(data),
      }
    );
  },
};
