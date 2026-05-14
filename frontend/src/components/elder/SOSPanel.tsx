import React from 'react';
import { useElderStore } from '@/store/elderStore';
import { AlertTriangle, Phone, Shield, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const SOSPanel: React.FC = () => {
  const { emergency, triggerEmergency, resolveEmergency } = useElderStore();

  if (emergency.active) {
    return (
      <div className="bg-destructive/5 border-2 border-destructive/30 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-destructive/20 flex items-center justify-center animate-pulse">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <h3 className="font-heading text-lg font-bold text-destructive">Emergency Active</h3>
              <p className="text-sm text-muted-foreground">Triggered {emergency.triggeredBy ? `by ${emergency.triggeredBy}` : ''}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={resolveEmergency}>
            <X className="w-4 h-4 mr-1" /> Resolve
          </Button>
        </div>

        <div className="space-y-2">
          {emergency.updates.map((u, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${i === emergency.updates.length - 1 ? 'bg-destructive animate-pulse' : 'bg-success'}`} />
              <span className="text-foreground">{u.message}</span>
              <span className="text-xs text-muted-foreground ml-auto">{new Date(u.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <button
        onClick={() => triggerEmergency('button')}
        className="flex-1 bg-destructive/10 hover:bg-destructive/20 border-2 border-destructive/30 rounded-2xl p-4 flex flex-col items-center gap-2 transition-all"
      >
        <Shield className="w-8 h-8 text-destructive" />
        <span className="text-sm font-semibold text-destructive">SOS Emergency</span>
      </button>
      <button className="flex-1 bg-info/10 hover:bg-info/20 border-2 border-info/30 rounded-2xl p-4 flex flex-col items-center gap-2 transition-all">
        <Phone className="w-8 h-8 text-info" />
        <span className="text-sm font-semibold text-info">Call Family</span>
      </button>
    </div>
  );
};

export default SOSPanel;

