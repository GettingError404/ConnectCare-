'use client';

import SettingsPage from '@/components/family/SettingsPage';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function SettingsRoutePage() {
  return (
    <AuthGuard>
      <SettingsPage />
    </AuthGuard>
  );
}
