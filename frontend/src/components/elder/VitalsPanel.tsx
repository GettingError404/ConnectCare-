import React from 'react';
import { useElderStore } from '@/store/elderStore';
import { Heart, Activity, Droplets, Thermometer, Wind, Footprints, TrendingUp } from 'lucide-react';

const vitalIcons: Record<string, React.ReactNode> = {
  heart_rate: <Heart className="w-5 h-5" />,
  blood_pressure: <Activity className="w-5 h-5" />,
  glucose: <Droplets className="w-5 h-5" />,
  activity: <Footprints className="w-5 h-5" />,
  spo2: <Wind className="w-5 h-5" />,
  temperature: <Thermometer className="w-5 h-5" />,
};

const vitalLabels: Record<string, string> = {
  heart_rate: 'Heart Rate',
  blood_pressure: 'Blood Pressure',
  glucose: 'Glucose',
  activity: 'Daily Steps',
  spo2: 'Oxygen (SpO₂)',
  temperature: 'Temperature',
};

const statusBg: Record<string, string> = {
  normal: 'bg-success/10 text-success ring-success/15',
  warning: 'bg-warning/10 text-warning ring-warning/15',
  critical: 'bg-destructive/10 text-destructive ring-destructive/15',
};

const statusLabel: Record<string, string> = {
  normal: 'Normal',
  warning: 'Watch',
  critical: 'Alert',
};

const VitalsPanel: React.FC = () => {
  const { vitals } = useElderStore();

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <h3 className="font-heading text-xl font-semibold text-foreground tracking-tight">Health Vitals</h3>
          <p className="text-sm text-muted-foreground mt-0.5">Live readings from your devices</p>
        </div>
        <span className="text-xs text-muted-foreground flex items-center gap-1">
          <TrendingUp className="w-3.5 h-3.5" /> Updated just now
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {vitals.map(v => (
          <div key={v.id} className="card-elevated rounded-2xl p-4 transition-shadow hover:shadow-md">
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ring-1 ${statusBg[v.status]}`}>
                {vitalIcons[v.type]}
              </div>
              <span className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ring-1 ${statusBg[v.status]}`}>
                {statusLabel[v.status]}
              </span>
            </div>
            <p className="text-xs text-muted-foreground font-medium">{vitalLabels[v.type]}</p>
            <p className="text-2xl font-bold text-foreground mt-0.5 tracking-tight">
              {v.value}
              <span className="text-xs font-medium text-muted-foreground ml-1">{v.unit}</span>
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VitalsPanel;

