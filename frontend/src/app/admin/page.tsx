'use client';

import { AuthGuard } from '@/components/auth/AuthGuard';
import FamilyDashboardContent from '@/components/family/FamilyDashboardContent';

export default function AdminPage() {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="bg-card rounded-3xl border border-border p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-[0.2em]">Admin dashboard</p>
                <h1 className="font-heading text-3xl font-semibold text-foreground">ConnectedCare+ Operations</h1>
              </div>
              <div className="rounded-3xl bg-muted px-4 py-3 text-sm font-medium text-foreground">Enterprise mode</div>
            </div>
          </div>

          <FamilyDashboardContent />
        </div>
      </div>
    </AuthGuard>
  );
}
