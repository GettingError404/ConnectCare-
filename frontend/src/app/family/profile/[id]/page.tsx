'use client';

import { useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useCaregiverStore } from '@/store/caregiverStore';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { Heart, Activity, ShieldCheck, Users } from 'lucide-react';

export default function FamilyProfilePage() {
  const { id } = useParams<{ id: string }>();

  const router = useRouter();
  const { assignedElders } = useCaregiverStore();

  const elder = useMemo(() => assignedElders.find((item) => item.elderId === id), [assignedElders, id]);
  if (!elder) {
    if (typeof window !== 'undefined') router.replace('/family/dashboard');
    return null;
  }

  return (
    <AuthGuard allowedRoles={['family']}>
      <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
        <div className="max-w-5xl mx-auto space-y-6">
          <div className="bg-card rounded-3xl border border-border p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Resident profile</p>
                <h1 className="font-heading text-3xl font-bold text-foreground">{elder.name}</h1>
              </div>
              <div className="rounded-3xl border border-border bg-muted px-4 py-3 text-sm font-medium text-foreground">{elder.status.toUpperCase()}</div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="card-elevated rounded-3xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">Key metrics</p>
                <Heart className="w-5 h-5 text-primary" />
              </div>
              <div className="grid gap-3">
                <div className="rounded-2xl bg-muted p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Age</p>
                  <p className="font-semibold text-foreground">{elder.age}</p>
                </div>
                <div className="rounded-2xl bg-muted p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Medication adherence</p>
                  <p className="font-semibold text-foreground">{elder.medicationAdherence}%</p>
                </div>
                <div className="rounded-2xl bg-muted p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Cognitive score</p>
                  <p className="font-semibold text-foreground">{elder.cognitiveScore}</p>
                </div>
              </div>
            </div>

            <div className="card-elevated rounded-3xl p-5">
              <p className="text-sm text-muted-foreground mb-3">Health profile</p>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-warning" />
                  <p className="text-sm text-foreground">Last check-in: {elder.lastCheckIn}</p>
                </div>
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-high" />
                  <p className="text-sm text-foreground">Risk: {elder.riskLevel}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Users className="w-5 h-5 text-primary" />
                  <p className="text-sm text-foreground">Mood trend: {elder.moodTrend}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-card rounded-3xl border border-border p-6">
            <h2 className="font-heading text-xl font-semibold text-foreground mb-4">Care history</h2>
            <p className="text-sm text-muted-foreground">This resident profile page preserves the look and feel of the current ConnectedCare+ platform while showing the selected elder's data.</p>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
