import React from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';

const statusBadge: Record<string, { color: string; icon: React.ReactNode }> = {
  completed: { color: 'bg-success/10 text-success', icon: <CheckCircle className="w-3.5 h-3.5" /> },
  due_soon: { color: 'bg-warning/10 text-warning', icon: <Clock className="w-3.5 h-3.5" /> },
  overdue: { color: 'bg-destructive/10 text-destructive', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  scheduled: { color: 'bg-info/10 text-info', icon: <Clock className="w-3.5 h-3.5" /> },
};

const checkItems = [
  { key: 'healthRiskAssessment', label: 'Health Risk Assessment' },
  { key: 'depressionScreening', label: 'Depression Screening' },
  { key: 'cognitiveAssessment', label: 'Cognitive Assessment' },
  { key: 'fallRiskAssessment', label: 'Fall Risk Assessment' },
  { key: 'advanceCarePlanning', label: 'Advance Care Planning' },
  { key: 'medicationReconciliation', label: 'Medication Reconciliation' },
] as const;

const CaregiverAWVPage: React.FC = () => {
  const { awvRecords } = useCaregiverStore();

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Annual Wellness Visit Tracking</h2>
        <p className="text-sm text-muted-foreground">AWV compliance and preventive care status</p>
      </div>

      <div className="space-y-4">
        {awvRecords.map(r => {
          const badge = statusBadge[r.status];
          return (
            <div key={r.elderId} className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-foreground">{r.elderName}</h3>
                  <p className="text-xs text-muted-foreground">
                    Last visit: {new Date(r.lastVisitDate).toLocaleDateString()} · Next due: {new Date(r.nextDueDate).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold ${badge.color}`}>
                    {badge.icon} {r.status.replace('_', ' ').toUpperCase()}
                  </span>
                  <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                    <span className={`text-sm font-bold ${r.score >= 80 ? 'text-success' : r.score >= 50 ? 'text-warning' : 'text-destructive'}`}>{r.score}%</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {checkItems.map(ci => {
                  const done = r[ci.key];
                  return (
                    <div key={ci.key} className={`flex items-center gap-2 p-2 rounded-lg text-xs ${done ? 'bg-success/5' : 'bg-destructive/5'}`}>
                      {done ? <CheckCircle className="w-3.5 h-3.5 text-success" /> : <XCircle className="w-3.5 h-3.5 text-destructive" />}
                      <span className={done ? 'text-foreground' : 'text-muted-foreground'}>{ci.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CaregiverAWVPage;

