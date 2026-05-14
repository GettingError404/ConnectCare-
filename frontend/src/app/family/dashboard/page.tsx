'use client';

import FamilyDashboard from '@/pages_legacy/FamilyDashboard';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function FamilyDashboardPage() {
  return (
    <AuthGuard allowedRoles={['family']}>
      <FamilyDashboard />
    </AuthGuard>
  );
}
