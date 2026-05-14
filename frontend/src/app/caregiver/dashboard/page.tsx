'use client';

import CaregiverDashboard from '@/pages_legacy/CaregiverDashboard';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function CaregiverDashboardPage() {
  return (
    <AuthGuard allowedRoles={['caregiver']}>
      <CaregiverDashboard />
    </AuthGuard>
  );
}
