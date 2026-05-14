import React from 'react';
import { Mic, Volume2, Loader2, AlertCircle } from 'lucide-react';
import { VoiceState } from '@/hooks/useVoiceEngine';

interface VoiceOrbProps {
  state: VoiceState;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

const config: Record<VoiceState, { ring: string; bg: string; label: string; sub: string }> = {
  idle:       { ring: 'ring-border',         bg: 'bg-card',                  label: 'Tap to talk',     sub: 'Voice assistant ready' },
  listening:  { ring: 'ring-primary/40',     bg: 'bg-primary text-primary-foreground', label: 'Listening',  sub: 'Speak naturally' },
  processing: { ring: 'ring-info/40',        bg: 'bg-info text-info-foreground',       label: 'Thinking',   sub: 'Processing your request' },
  speaking:   { ring: 'ring-success/40',     bg: 'bg-success text-success-foreground', label: 'Speaking',   sub: 'Tap to interrupt' },
  error:      { ring: 'ring-destructive/40', bg: 'bg-destructive text-destructive-foreground', label: 'Try again', sub: 'Something went wrong' },
};

const VoiceOrb: React.FC<VoiceOrbProps> = ({ state, onClick, disabled, className = '' }) => {
  const c = config[state];

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      <div className="relative flex items-center justify-center">
        {state === 'listening' && (
          <>
            <div className="absolute w-40 h-40 rounded-full border border-primary/25 pulse-ring" />
            <div className="absolute w-52 h-52 rounded-full border border-primary/15 pulse-ring" style={{ animationDelay: '0.6s' }} />
          </>
        )}
        {state === 'speaking' && (
          <div className="absolute w-44 h-44 rounded-full border border-success/25 pulse-ring" />
        )}

        <button
          onClick={onClick}
          disabled={disabled}
          aria-label={c.label}
          className={`relative w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 hover:scale-[1.03] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ring-4 ${c.ring} ${c.bg} shadow-lg focus-ring`}
        >
          {state === 'listening' && <Mic className="w-10 h-10" strokeWidth={2} />}
          {state === 'speaking' && (
            <div className="flex items-end gap-1 h-10">
              {[0, 1, 2, 3, 4].map(i => (
                <span
                  key={i}
                  className="w-1.5 bg-current rounded-full"
                  style={{
                    height: `${30 + (i % 2 === 0 ? 10 : -6)}px`,
                    animation: `waveform-bar 0.7s ease-in-out ${i * 0.12}s infinite`,
                  }}
                />
              ))}
            </div>
          )}
          {state === 'processing' && <Loader2 className="w-10 h-10 animate-spin" strokeWidth={2} />}
          {state === 'idle' && <Mic className="w-10 h-10 text-muted-foreground" strokeWidth={2} />}
          {state === 'error' && <AlertCircle className="w-10 h-10" strokeWidth={2} />}
        </button>
      </div>

      <div className="text-center">
        <p className={`text-base font-semibold ${
          state === 'listening' ? 'text-primary' :
          state === 'speaking' ? 'text-success' :
          state === 'processing' ? 'text-info' :
          state === 'error' ? 'text-destructive' :
          'text-foreground'
        }`}>
          {c.label}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">{c.sub}</p>
      </div>
    </div>
  );
};

export default VoiceOrb;
