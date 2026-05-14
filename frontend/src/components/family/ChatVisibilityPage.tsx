import React from 'react';
import { useElderStore } from '@/store/elderStore';
import { ChatMessage } from '@/types';

const ChatVisibilityPage: React.FC = () => {
  const { chatMessages } = useElderStore();

  // Filter to last 24 hours
  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  const recentMessages = chatMessages.filter(m => new Date(m.timestamp).getTime() > cutoff);

  return (
    <div className="space-y-4 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">24-Hour Chat</h2>
        <p className="text-sm text-muted-foreground">AI companion conversation with Margaret (last 24 hours)</p>
      </div>

      <div className="space-y-3">
        {recentMessages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-primary/10 text-foreground rounded-br-md'
                : 'bg-muted text-foreground rounded-bl-md'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium">{msg.role === 'user' ? '👵 Margaret' : '🤖 AI Companion'}</span>
                <span className="text-[10px] text-muted-foreground">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <p className="text-sm">{msg.content}</p>
              {msg.tags && msg.tags.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {msg.tags.map(tag => (
                    <span key={tag} className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {recentMessages.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-12">No conversations in the last 24 hours</p>
        )}
      </div>
    </div>
  );
};

export default ChatVisibilityPage;

