'use client';

import ElderHeader from '@/components/elder/ElderHeader';
import VitalsPanel from '@/components/elder/VitalsPanel';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function ElderWellnessPage() {
  return (
    <AuthGuard allowedRoles={['elder']}>
      <div className="min-h-screen bg-elder-bg">
        <ElderHeader />
        <main className="mx-auto max-w-3xl px-4 py-6">
          <VitalsPanel />
        </main>
      </div>
    </AuthGuard>
  );
}
