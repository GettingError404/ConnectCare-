import React from 'react';
import { Music, BookOpen, Smile, Brain, HelpCircle, Type } from 'lucide-react';

interface EntertainmentPanelProps {
  onVoiceCommand: (text: string) => void;
}

const cards = [
  { icon: Music, label: 'Music', command: 'play some music' },
  { icon: BookOpen, label: 'Story', command: 'tell me a story' },
  { icon: Smile, label: 'Joke', command: 'tell me a joke' },
  { icon: Brain, label: 'Memory', command: 'play memory game' },
  { icon: HelpCircle, label: 'Quiz', command: 'play quiz game' },
  { icon: Type, label: 'Word', command: 'play word game' },
];

const EntertainmentPanel: React.FC<EntertainmentPanelProps> = ({ onVoiceCommand }) => {
  return (
    <div className="grid grid-cols-3 gap-2.5 w-full max-w-md mx-auto">
      {cards.map(card => {
        const Icon = card.icon;
        return (
          <button
            key={card.label}
            onClick={() => onVoiceCommand(card.command)}
            className="flex flex-col items-center gap-2 p-3.5 rounded-xl bg-card border border-border hover:border-primary/40 hover:shadow-sm active:scale-[0.97] transition-all focus-ring"
          >
            <div className="w-10 h-10 rounded-lg bg-primary/8 text-primary flex items-center justify-center">
              <Icon className="w-5 h-5" strokeWidth={2.25} />
            </div>
            <span className="text-xs font-semibold text-foreground">{card.label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default EntertainmentPanel;
