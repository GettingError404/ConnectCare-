'use client';

import CaregiverPatientsPage from '@/components/caregiver/CaregiverPatientsPage';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function CaregiverResidentsPage() {
  return (
    <AuthGuard allowedRoles={['caregiver']}>
      <CaregiverPatientsPage />
    </AuthGuard>
  );
}
