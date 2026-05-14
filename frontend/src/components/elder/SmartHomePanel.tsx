import React from 'react';
import { useElderStore } from '@/store/elderStore';
import { Lightbulb, Lock, DoorOpen, Thermometer } from 'lucide-react';
import { SmartDevice } from '@/types';

const deviceIcons: Record<string, React.ReactNode> = {
  light: <Lightbulb className="w-5 h-5" />,
  lock: <Lock className="w-5 h-5" />,
  door: <DoorOpen className="w-5 h-5" />,
  thermostat: <Thermometer className="w-5 h-5" />,
};

const DeviceCard: React.FC<{ device: SmartDevice; onToggle: (id: string) => void }> = ({ device, onToggle }) => {
  const isActive = device.status === 'on' || device.status === 'unlocked' || device.status === 'open';

  return (
    <button
      onClick={() => onToggle(device.id)}
      className={`rounded-xl border p-3 text-left transition-all ${
        isActive ? 'bg-primary/10 border-primary/30' : 'bg-card border-border'
      } hover:shadow-md`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${isActive ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
        {deviceIcons[device.type]}
      </div>
      <p className="text-sm font-medium text-foreground truncate">{device.name}</p>
      <p className="text-xs text-muted-foreground">{device.room}</p>
      <p className={`text-xs font-medium mt-1 ${isActive ? 'text-primary' : 'text-muted-foreground'}`}>
        {device.status}{device.type === 'thermostat' && device.value ? ` · ${device.value}°F` : ''}
      </p>
    </button>
  );
};

const SmartHomePanel: React.FC = () => {
  const { smartDevices, toggleDevice } = useElderStore();

  return (
    <div className="space-y-3">
      <h3 className="font-heading text-lg font-semibold text-foreground">Smart Home</h3>
      <div className="grid grid-cols-3 gap-2">
        {smartDevices.map(d => (
          <DeviceCard key={d.id} device={d} onToggle={toggleDevice} />
        ))}
      </div>
    </div>
  );
};

export default SmartHomePanel;

