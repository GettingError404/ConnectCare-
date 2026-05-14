'use client';

import SmartHomeFamilyPage from '@/components/family/SmartHomeFamilyPage';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function SmartHomePage() {
  return (
    <AuthGuard>
      <SmartHomeFamilyPage />
    </AuthGuard>
  );
}
