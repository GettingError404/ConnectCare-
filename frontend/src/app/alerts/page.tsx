'use client';

import AlertsPage from '@/components/family/AlertsPage';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function AlertsRootPage() {
  return (
    <AuthGuard>
      <AlertsPage />
    </AuthGuard>
  );
}
