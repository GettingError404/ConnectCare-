'use client';

import ElderHeader from '@/components/elder/ElderHeader';
import RemindersPanel from '@/components/elder/RemindersPanel';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function ElderMedicationsPage() {
  return (
    <AuthGuard allowedRoles={['elder']}>
      <div className="min-h-screen bg-elder-bg">
        <ElderHeader />
        <main className="mx-auto max-w-3xl px-4 py-6">
          <RemindersPanel />
        </main>
      </div>
    </AuthGuard>
  );
}
