import React from 'react';
import { PhoneCall, ShieldAlert, Pill, HeartPulse } from 'lucide-react';

interface QuickActionsProps {
  onVoiceCommand: (text: string) => void;
}

const actions = [
  { icon: PhoneCall, label: 'Call Family', command: 'call my family', tone: 'primary' },
  { icon: ShieldAlert, label: 'Emergency', command: 'help me emergency', tone: 'destructive' },
  { icon: Pill, label: 'Medicines', command: 'show my reminders', tone: 'warning' },
  { icon: HeartPulse, label: 'My Health', command: 'show my health', tone: 'success' },
] as const;

const toneClasses: Record<string, string> = {
  primary: 'bg-primary/8 text-primary ring-primary/15 hover:bg-primary/12',
  destructive: 'bg-destructive/8 text-destructive ring-destructive/15 hover:bg-destructive/12',
  warning: 'bg-warning/10 text-warning ring-warning/15 hover:bg-warning/15',
  success: 'bg-success/8 text-success ring-success/15 hover:bg-success/12',
};

const QuickActions: React.FC<QuickActionsProps> = ({ onVoiceCommand }) => {
  return (
    <div className="grid grid-cols-4 gap-2 max-w-md mx-auto">
      {actions.map(a => {
        const Icon = a.icon;
        return (
          <button
            key={a.label}
            onClick={() => onVoiceCommand(a.command)}
            className={`flex flex-col items-center justify-center gap-1.5 px-2 py-3 rounded-xl ring-1 transition-all active:scale-[0.97] focus-ring ${toneClasses[a.tone]}`}
          >
            <Icon className="w-5 h-5" strokeWidth={2.25} />
            <span className="text-[11px] font-semibold leading-none text-foreground">{a.label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default QuickActions;
