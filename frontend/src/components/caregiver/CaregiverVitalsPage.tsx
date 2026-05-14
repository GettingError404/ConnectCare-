import React from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { Heart, Droplets, Activity, Wind } from 'lucide-react';

const typeIcon: Record<string, React.ReactNode> = {
  heart_rate: <Heart className="w-4 h-4 text-destructive" />,
  blood_pressure: <Activity className="w-4 h-4 text-primary" />,
  glucose: <Droplets className="w-4 h-4 text-warning" />,
  spo2: <Wind className="w-4 h-4 text-info" />,
};

const statusColor: Record<string, string> = {
  normal: 'text-success',
  warning: 'text-warning',
  critical: 'text-destructive',
};

const CaregiverVitalsPage: React.FC = () => {
  const { assignedElders, elderVitals } = useCaregiverStore();

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Vitals Monitor</h2>
        <p className="text-sm text-muted-foreground">Real-time vitals across all patients</p>
      </div>

      {assignedElders.map(elder => {
        const vitals = elderVitals[elder.elderId] || [];
        return (
          <div key={elder.elderId} className="bg-card rounded-xl border border-border p-5">
            <div className="flex items-center gap-2 mb-4">
              <span className={`w-2 h-2 rounded-full ${elder.status === 'online' ? 'bg-success' : 'bg-muted-foreground'}`} />
              <h3 className="font-semibold text-foreground">{elder.name}</h3>
              <span className="text-xs text-muted-foreground">· Age {elder.age}</span>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {vitals.map(v => (
                <div key={v.id} className="bg-muted/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    {typeIcon[v.type]}
                    <span className="text-[10px] text-muted-foreground capitalize">{v.type.replace('_', ' ')}</span>
                  </div>
                  <p className={`text-xl font-bold ${statusColor[v.status]}`}>{v.value}</p>
                  <p className="text-[10px] text-muted-foreground">{v.unit}</p>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CaregiverVitalsPage;

