'use client';

import ElderDashboard from '@/pages_legacy/ElderDashboard';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function ElderPage() {
  return (
    <AuthGuard allowedRoles={['elder']}>
      <ElderDashboard />
    </AuthGuard>
  );
}
