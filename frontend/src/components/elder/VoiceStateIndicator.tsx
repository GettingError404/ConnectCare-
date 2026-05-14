import React from 'react';
import { Mic, Loader2, Volume2, MicOff } from 'lucide-react';
import { VoiceState } from '@/hooks/useVoiceEngine';

interface VoiceStateIndicatorProps {
  state: VoiceState;
  transcript?: string;
  className?: string;
}

const stateConfig: Record<VoiceState, { label: string; color: string; bgColor: string; icon: React.ReactNode; animate: string }> = {
  idle: { label: 'Tap to speak', color: 'text-muted-foreground', bgColor: 'bg-muted', icon: <MicOff className="w-5 h-5" />, animate: '' },
  listening: { label: 'Listening...', color: 'text-primary', bgColor: 'bg-primary/10', icon: <Mic className="w-5 h-5" />, animate: 'animate-pulse' },
  processing: { label: 'Thinking...', color: 'text-info', bgColor: 'bg-info/10', icon: <Loader2 className="w-5 h-5 animate-spin" />, animate: '' },
  speaking: { label: 'Speaking...', color: 'text-success', bgColor: 'bg-success/10', icon: <Volume2 className="w-5 h-5" />, animate: 'animate-pulse' },
  error: { label: 'Error', color: 'text-destructive', bgColor: 'bg-destructive/10', icon: <MicOff className="w-5 h-5" />, animate: '' },
};

const VoiceStateIndicator: React.FC<VoiceStateIndicatorProps> = ({ state, transcript, className = '' }) => {
  const config = stateConfig[state];

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className={`relative flex items-center justify-center w-10 h-10 rounded-full ${config.bgColor} ${config.color} ${config.animate}`}>
        {config.icon}
        {state === 'listening' && (
          <>
            <div className="absolute inset-0 rounded-full border-2 border-primary/40 pulse-ring" />
            <div className="absolute -inset-1 rounded-full border border-primary/20 pulse-ring" style={{ animationDelay: '0.5s' }} />
          </>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${config.color}`}>{config.label}</p>
        {state === 'listening' && transcript && (
          <p className="text-xs text-muted-foreground truncate italic">"{transcript}"</p>
        )}
      </div>
    </div>
  );
};

export default VoiceStateIndicator;
