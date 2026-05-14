import React from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { ShieldCheck, AlertTriangle, TrendingDown } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

const statusColor: Record<string, string> = {
  on_track: 'bg-success/10 text-success border-success/30',
  at_risk: 'bg-warning/10 text-warning border-warning/30',
  non_compliant: 'bg-destructive/10 text-destructive border-destructive/30',
};

const CaregiverChronicCarePage: React.FC = () => {
  const { chronicCare } = useCaregiverStore();

  const grouped = chronicCare.reduce((acc, c) => {
    if (!acc[c.elderName]) acc[c.elderName] = [];
    acc[c.elderName].push(c);
    return acc;
  }, {} as Record<string, typeof chronicCare>);

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Chronic Care Compliance</h2>
        <p className="text-sm text-muted-foreground">Long-term treatment plan monitoring</p>
      </div>

      {Object.entries(grouped).map(([name, records]) => (
        <div key={name} className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">{name}</h3>
          {records.map((c, i) => (
            <div key={i} className={`rounded-xl border-2 p-4 ${statusColor[c.status]}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4" />
                  <h4 className="font-semibold text-foreground text-sm">{c.condition}</h4>
                </div>
                <span className="text-[10px] font-bold uppercase">{c.status.replace('_', ' ')}</span>
              </div>
              <p className="text-xs text-muted-foreground mb-3">{c.treatmentPlan}</p>

              <div className="mb-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Adherence</span>
                  <span className={`font-bold ${c.adherence < 50 ? 'text-destructive' : c.adherence < 75 ? 'text-warning' : 'text-success'}`}>{c.adherence}%</span>
                </div>
                <Progress value={c.adherence} className="h-2" />
              </div>

              <p className="text-[10px] text-muted-foreground">
                Last review: {new Date(c.lastReview).toLocaleDateString()} · Next: {new Date(c.nextReview).toLocaleDateString()}
              </p>

              {c.alerts.length > 0 && (
                <div className="mt-2 space-y-1">
                  {c.alerts.map((alert, ai) => (
                    <div key={ai} className="flex items-center gap-1.5 text-[11px]">
                      <AlertTriangle className="w-3 h-3 text-warning" />
                      <span className="text-foreground">{alert}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default CaregiverChronicCarePage;

