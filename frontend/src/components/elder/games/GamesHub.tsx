'use client';
import React, { useState } from 'react';
import { Brain, Type, Palette, Users, ArrowLeft, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import MemoryMatchGame from './MemoryMatchGame';
import WordClueGame from './WordClueGame';
import ColoringGame from './ColoringGame';
import SeniorClub from './SeniorClub';

type ActiveGame = 'menu' | 'memory' | 'word' | 'coloring' | 'club';

interface GamesHubProps {
  onSpeak: (text: string) => void;
  onBack: () => void;
  initialGame?: ActiveGame;
}

const gameOptions = [
  { id: 'memory' as ActiveGame, icon: Brain,   label: 'Memory Match', desc: 'Find matching pairs',  tone: 'bg-primary/10 text-primary ring-primary/15' },
  { id: 'word' as ActiveGame,   icon: Type,    label: 'Word Clue',    desc: 'Guess the word aloud', tone: 'bg-info/10 text-info ring-info/15' },
  { id: 'coloring' as ActiveGame, icon: Palette, label: 'Coloring',   desc: 'Tap to fill colors',   tone: 'bg-warning/10 text-warning ring-warning/15' },
  { id: 'club' as ActiveGame,   icon: Users,   label: 'Senior Club',  desc: 'Play with friends',    tone: 'bg-success/10 text-success ring-success/15' },
];

const GamesHub: React.FC<GamesHubProps> = ({ onSpeak, onBack, initialGame = 'menu' }) => {
  const [activeGame, setActiveGame] = useState<ActiveGame>(initialGame);

  const exitToMenu = () => {
    setActiveGame('menu');
    onSpeak('Choose a game or join the Senior Club!');
  };

  if (activeGame === 'memory')   return <MemoryMatchGame onExit={exitToMenu} onSpeak={onSpeak} />;
  if (activeGame === 'word')     return <WordClueGame onExit={exitToMenu} onSpeak={onSpeak} />;
  if (activeGame === 'coloring') return <ColoringGame onExit={exitToMenu} onSpeak={onSpeak} />;
  if (activeGame === 'club')     return <SeniorClub onExit={exitToMenu} onSpeak={onSpeak} />;

  return (
    <div className="flex flex-col gap-5 max-w-2xl mx-auto py-2 animate-fade-in">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back">
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="text-center">
          <h2 className="font-heading text-xl font-semibold text-foreground tracking-tight">Games & Companionship</h2>
          <p className="text-xs text-muted-foreground mt-0.5">Tap a card or say its name</p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => onSpeak('Choose a game by tapping a card or saying its name.')} aria-label="Repeat">
          <Volume2 className="w-5 h-5" />
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {gameOptions.map(game => {
          const Icon = game.icon;
          return (
            <button
              key={game.id}
              onClick={() => setActiveGame(game.id)}
              className="group flex flex-col items-start gap-3 p-5 rounded-2xl bg-card border border-border hover:border-primary/40 hover:shadow-md active:scale-[0.98] transition-all text-left focus-ring"
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ring-1 ${game.tone}`}>
                <Icon className="w-6 h-6" strokeWidth={2.25} />
              </div>
              <div>
                <p className="text-base font-semibold text-foreground">{game.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{game.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default GamesHub;
export type { ActiveGame };

