'use client';

import EmergencyTelehealthPage from '@/components/family/EmergencyTelehealthPage';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function TelehealthPage() {
  return (
    <AuthGuard>
      <EmergencyTelehealthPage />
    </AuthGuard>
  );
}
