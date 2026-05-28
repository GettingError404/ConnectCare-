'use client';
import React, { useRef, useEffect, useState } from 'react';
import { Mic, MicOff, Volume2, Send, Power } from 'lucide-react';
import { useElderStore } from '@/store/elderStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import VoiceStateIndicator from './VoiceStateIndicator';
import { VoiceState } from '@/hooks/useVoiceEngine';

interface VoiceCompanionProps {
  voiceState: VoiceState;
  continuousMode: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  speechError: string | null;
  sttSupported: boolean;
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'reconnecting';
  liveResponse: string;
  assistantDraft: string;
  onToggleContinuous: () => void;
  onProcessText: (text: string) => void;
  onCancelSpeech: () => void;
}

const VoiceCompanion: React.FC<VoiceCompanionProps> = ({
  voiceState,
  continuousMode,
  isListening,
  isSpeaking,
  transcript,
  speechError,
  sttSupported,
  connectionStatus,
  liveResponse,
  assistantDraft,
  onToggleContinuous,
  onProcessText,
  onCancelSpeech,
}) => {
  const { chatMessages } = useElderStore();
  const [textInput, setTextInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const handleSendText = () => {
    if (!textInput.trim()) return;
    onProcessText(textInput.trim());
    setTextInput('');
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const connectionLabel = connectionStatus === 'connected'
    ? 'Connected'
    : connectionStatus === 'connecting'
      ? 'Connecting...'
      : connectionStatus === 'reconnecting'
        ? 'Reconnecting...'
        : 'Disconnected';

  return (
    <div className="flex flex-col h-full">
      {/* Voice State Bar */}
      <div className="px-4 py-2 border-b border-border bg-card flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <VoiceStateIndicator state={voiceState} transcript={transcript} />
          <div className="rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground">
            {connectionLabel}
          </div>
        </div>
        <button
          onClick={onToggleContinuous}
          disabled={!sttSupported}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
            continuousMode
              ? 'bg-primary text-primary-foreground shadow-md'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          <Power className="w-3.5 h-3.5" />
          {continuousMode ? 'Voice ON' : 'Voice OFF'}
        </button>
      </div>

      {/* Chat Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {chatMessages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-primary text-primary-foreground rounded-br-md'
                : 'bg-muted text-foreground rounded-bl-md'
            }`}>
              <p className="elder-text-base leading-relaxed">{msg.content}</p>
              <p className="text-[10px] mt-1 opacity-60">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                {msg.tags?.map(t => <span key={t} className="ml-1 opacity-50">#{t}</span>)}
              </p>
            </div>
          </div>
        ))}

        {isListening && transcript && (
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-primary/20 text-foreground rounded-br-md border border-primary/30">
              <p className="elder-text-base italic">{transcript}...</p>
            </div>
          </div>
        )}

        {(liveResponse || assistantDraft) && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-secondary/10 text-foreground rounded-bl-md border border-secondary/30">
              <p className="elder-text-base leading-relaxed">{liveResponse || assistantDraft}</p>
              <p className="text-[10px] mt-1 opacity-60">Assistant response streaming</p>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Voice Control Area */}
      <div className="border-t border-border bg-card p-4">
        {/* Big Mic Button */}
        <div className="flex justify-center mb-4">
          <button
            onClick={voiceState === 'speaking' ? onCancelSpeech : onToggleContinuous}
            disabled={!sttSupported}
            className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg ${
              continuousMode
                ? voiceState === 'listening'
                  ? 'bg-primary text-primary-foreground scale-110'
                  : voiceState === 'speaking'
                  ? 'bg-success text-success-foreground scale-105'
                  : voiceState === 'processing'
                  ? 'bg-info text-info-foreground scale-105'
                  : 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-primary hover:text-primary-foreground hover:scale-105'
            }`}
          >
            {voiceState === 'listening' ? (
              <div className="relative">
                <Mic className="w-8 h-8" />
                <div className="absolute -inset-3 rounded-full border-2 border-primary-foreground/40 pulse-ring" />
                <div className="absolute -inset-5 rounded-full border border-primary-foreground/20 pulse-ring" style={{ animationDelay: '0.5s' }} />
              </div>
            ) : voiceState === 'speaking' ? (
              <Volume2 className="w-8 h-8 animate-pulse" />
            ) : voiceState === 'processing' ? (
              <div className="w-8 h-8 border-3 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <Mic className="w-8 h-8" />
            )}
          </button>
        </div>

        <p className="text-center text-sm text-muted-foreground mb-3">
          {voiceState === 'listening' && '🎤 Listening — speak naturally...'}
          {voiceState === 'processing' && '🧠 Processing your request...'}
          {voiceState === 'speaking' && '🔊 Speaking — tap to interrupt'}
          {voiceState === 'idle' && (continuousMode ? '⏳ Getting ready...' : 'Tap the mic to activate voice assistant')}
          {voiceState === 'error' && '❌ Voice error — try again or type below'}
        </p>

        {speechError && <p className="text-center text-xs text-destructive mb-2">{speechError}</p>}

        {/* Text fallback */}
        <div className="flex gap-2">
          <Input
            placeholder="Or type a message..."
            value={textInput}
            onChange={e => setTextInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSendText()}
            className="elder-text-base"
          />
          <Button onClick={handleSendText} size="icon" className="shrink-0">
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default VoiceCompanion;


