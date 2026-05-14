'use client';
import React, { useRef, useEffect } from 'react';
import { useElderStore } from '@/store/elderStore';

interface LiveTranscriptProps {
  liveTranscript?: string;
  isListening: boolean;
  maxMessages?: number;
}

const LiveTranscript: React.FC<LiveTranscriptProps> = ({ liveTranscript, isListening, maxMessages = 6 }) => {
  const { chatMessages } = useElderStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const recent = chatMessages.slice(-maxMessages);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, liveTranscript]);

  return (
    <div className="w-full max-w-md mx-auto space-y-2 overflow-y-auto max-h-48 px-2">
      {recent.map(msg => (
        <div
          key={msg.id}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
            msg.role === 'user'
              ? 'bg-primary text-primary-foreground rounded-br-sm'
              : 'bg-card border border-border text-foreground rounded-bl-sm'
          }`}>
            <p className="text-sm leading-relaxed">{msg.content}</p>
          </div>
        </div>
      ))}

      {isListening && liveTranscript && (
        <div className="flex justify-end">
          <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-primary/20 text-foreground rounded-br-sm border border-primary/30">
            <p className="text-sm italic">{liveTranscript}...</p>
          </div>
        </div>
      )}
      <div ref={scrollRef} />
    </div>
  );
};

export default LiveTranscript;


