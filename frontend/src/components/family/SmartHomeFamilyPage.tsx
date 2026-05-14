import React from 'react';
import { mockSmartDevices } from '@/data/mockData';
import { Lightbulb, Lock, DoorOpen, Thermometer, Shield } from 'lucide-react';

const deviceIcons: Record<string, React.ReactNode> = {
  light: <Lightbulb className="w-5 h-5" />,
  lock: <Lock className="w-5 h-5" />,
  door: <DoorOpen className="w-5 h-5" />,
  thermostat: <Thermometer className="w-5 h-5" />,
};

const SmartHomeFamilyPage: React.FC = () => {
  const devices = mockSmartDevices;

  const automations = [
    { id: 1, trigger: 'Fall detected', action: 'Turn on all lights', time: '2 days ago' },
    { id: 2, trigger: 'Sunset', action: 'Living room light on', time: '4 hours ago' },
    { id: 3, trigger: 'Night mode', action: 'Lock all doors', time: 'Yesterday, 10 PM' },
  ];

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">Smart Home & Safety</h2>
        <p className="text-sm text-muted-foreground">Home device status and safety automations</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {devices.map(d => {
          const isActive = d.status === 'on' || d.status === 'unlocked' || d.status === 'open';
          return (
            <div key={d.id} className={`rounded-xl border p-4 ${isActive ? 'bg-primary/5 border-primary/20' : 'bg-card border-border'}`}>
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-2 ${isActive ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
                {deviceIcons[d.type]}
              </div>
              <p className="text-sm font-medium text-foreground">{d.name}</p>
              <p className="text-xs text-muted-foreground">{d.room}</p>
              <p className={`text-xs font-medium mt-1 ${isActive ? 'text-primary' : 'text-muted-foreground'}`}>
                {d.status}{d.type === 'thermostat' && d.value ? ` · ${d.value}°F` : ''}
              </p>
            </div>
          );
        })}
      </div>

      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4 text-primary" /> Automation History
        </h3>
        <div className="space-y-2">
          {automations.map(a => (
            <div key={a.id} className="bg-card rounded-xl border border-border px-4 py-3 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">{a.trigger} → {a.action}</p>
                <span className="text-xs text-muted-foreground">{a.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SmartHomeFamilyPage;
