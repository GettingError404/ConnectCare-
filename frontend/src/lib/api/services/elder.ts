import type { ApiResponse } from '../types';
import { healthcareService, type ElderResponse } from './healthcare';

export interface ElderDashboardProfile {
  elder: ElderResponse;
  medicalProfile?: unknown;
}

export const elderService = {
  async getElder(elderId: string): Promise<ApiResponse<ElderResponse>> {
    return healthcareService.getElder(elderId);
  },

  async getMedicalProfile(elderId: string) {
    return healthcareService.getMedicalProfile(elderId);
  },

  async getDashboardProfile(elderId: string): Promise<ApiResponse<ElderDashboardProfile>> {
    const elderResponse = await healthcareService.getElder(elderId);
    if (!elderResponse.ok) return elderResponse as ApiResponse<ElderDashboardProfile>;

    const medicalResponse = await healthcareService.getMedicalProfile(elderId);
    return {
      ok: true,
      data: {
        elder: elderResponse.data,
        medicalProfile: medicalResponse.ok ? medicalResponse.data : undefined,
      },
    };
  },
};