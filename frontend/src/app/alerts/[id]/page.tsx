'use client';

import { useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useFamilyStore } from '@/store/familyStore';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AlertDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { alerts } = useFamilyStore();
  const alert = useMemo(() => alerts.find((item) => item.id === params.id), [alerts, params.id]);

  if (!alert) {
    if (typeof window !== 'undefined') router.replace('/alerts');
    return null;
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="bg-card rounded-3xl border border-border p-6">
            <div className="flex items-start gap-4">
              <div className="rounded-3xl bg-destructive/10 p-4 text-destructive">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-[0.2em]">Alert detail</p>
                <h1 className="font-heading text-3xl font-semibold text-foreground mt-2">{alert.title}</h1>
                <p className="text-sm text-muted-foreground mt-2">{new Date(alert.timestamp).toLocaleString()}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-3xl bg-muted p-5">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Severity</p>
                <p className="mt-2 font-semibold text-foreground">{alert.severity}</p>
              </div>
              <div className="rounded-3xl bg-muted p-5">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Status</p>
                <p className="mt-2 font-semibold text-foreground">{alert.status}</p>
              </div>
            </div>

            <div className="mt-6 rounded-3xl bg-card border border-border p-5">
              <h2 className="text-sm font-semibold text-foreground mb-2">Details</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">{alert.description}</p>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
              <Button onClick={() => router.back()}>Back to alerts</Button>
              <span className="text-sm text-muted-foreground">Recommended action: {alert.recommendedAction}</span>
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
