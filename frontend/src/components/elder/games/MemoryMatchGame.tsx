'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { RotateCcw, Volume2, X } from 'lucide-react';

interface Card {
  id: number;
  emoji: string;
  label: string;
  flipped: boolean;
  matched: boolean;
}

const CARD_ITEMS = [
  { emoji: '🍎', label: 'apple' },
  { emoji: '🌻', label: 'sunflower' },
  { emoji: '🏠', label: 'house' },
  { emoji: '⭐', label: 'star' },
  { emoji: '🐱', label: 'cat' },
  { emoji: '🌈', label: 'rainbow' },
];

interface MemoryMatchGameProps {
  onExit: () => void;
  onSpeak: (text: string) => void;
}

const MemoryMatchGame: React.FC<MemoryMatchGameProps> = ({ onExit, onSpeak }) => {
  const [cards, setCards] = useState<Card[]>([]);
  const [flippedIds, setFlippedIds] = useState<number[]>([]);
  const [matchCount, setMatchCount] = useState(0);
  const [moves, setMoves] = useState(0);
  const [gameOver, setGameOver] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [locked, setLocked] = useState(false);
  const pairCount = 4;

  const initGame = useCallback(() => {
    const selected = [...CARD_ITEMS].sort(() => Math.random() - 0.5).slice(0, pairCount);
    const paired = [...selected, ...selected]
      .sort(() => Math.random() - 0.5)
      .map((item, i) => ({ id: i, emoji: item.emoji, label: item.label, flipped: false, matched: false }));
    setCards(paired);
    setFlippedIds([]);
    setMatchCount(0);
    setMoves(0);
    setGameOver(false);
    setFeedback('');
    setLocked(false);
  }, []);

  useEffect(() => {
    initGame();
    onSpeak('Tap the cards to find matching pairs. Take your time!');
  }, []);

  const handleFlip = (id: number) => {
    if (locked) return;
    const card = cards[id];
    if (card.flipped || card.matched) return;

    const newCards = cards.map(c => c.id === id ? { ...c, flipped: true } : c);
    setCards(newCards);
    const newFlipped = [...flippedIds, id];
    setFlippedIds(newFlipped);

    if (newFlipped.length === 2) {
      setLocked(true);
      setMoves(m => m + 1);
      const [a, b] = newFlipped;
      if (newCards[a].emoji === newCards[b].emoji) {
        // Match found
        setTimeout(() => {
          setCards(prev => prev.map(c =>
            c.id === a || c.id === b ? { ...c, matched: true } : c
          ));
          setFlippedIds([]);
          const newMatch = matchCount + 1;
          setMatchCount(newMatch);
          setLocked(false);

          const msgs = ['Good job! 🎉', 'Well done! ⭐', 'Great memory! 🧠', 'Wonderful! 🌟'];
          const msg = msgs[Math.floor(Math.random() * msgs.length)];
          setFeedback(msg);
          onSpeak(msg);

          if (newMatch === pairCount) {
            setGameOver(true);
            setTimeout(() => onSpeak('You found all the pairs! Amazing job!'), 500);
          }
        }, 600);
      } else {
        // No match
        setTimeout(() => {
          setCards(prev => prev.map(c =>
            c.id === a || c.id === b ? { ...c, flipped: false } : c
          ));
          setFlippedIds([]);
          setLocked(false);
          setFeedback('Try again! 💪');
        }, 1200);
      }
    }
  };

  // Voice command handler
  const handleVoiceCommand = useCallback((command: string) => {
    const lower = command.toLowerCase();
    if (/repeat|instruction|help/.test(lower)) {
      onSpeak('Tap two cards to flip them. Find all matching pairs!');
    } else if (/restart|new|again/.test(lower)) {
      initGame();
      onSpeak('Starting a new game! Tap the cards to find matches.');
    } else if (/exit|quit|stop|back/.test(lower)) {
      onExit();
    }
  }, [initGame, onExit, onSpeak]);

  // Expose to parent
  useEffect(() => {
    type WindowWithMemoryMatchCommand = Window & {
      __memoryMatchCommand?: (command: string) => void;
    };

    (window as WindowWithMemoryMatchCommand).__memoryMatchCommand = handleVoiceCommand;
    return () => {
      delete (window as WindowWithMemoryMatchCommand).__memoryMatchCommand;
    };
  }, [handleVoiceCommand]);


  if (gameOver) {
    return (
      <div className="flex flex-col items-center justify-center gap-6 p-6 animate-fade-in">
        <div className="text-6xl">🎊</div>
        <h2 className="text-2xl font-bold text-foreground">You Did It!</h2>
        <p className="text-lg text-muted-foreground">All pairs found in {moves} moves</p>
        <div className="flex gap-3">
          <Button onClick={() => { initGame(); onSpeak('New game started! Find the matching pairs.'); }} size="lg" className="text-lg px-8 py-6 rounded-2xl">
            <RotateCcw className="w-5 h-5 mr-2" /> Play Again
          </Button>
          <Button onClick={onExit} variant="outline" size="lg" className="text-lg px-8 py-6 rounded-2xl">
            <X className="w-5 h-5 mr-2" /> Exit
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 p-4 animate-fade-in">
      <div className="flex items-center justify-between w-full max-w-md">
        <h2 className="text-xl font-bold text-foreground">🃏 Memory Match</h2>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={() => onSpeak('Tap two cards to flip them. Find all matching pairs!')}>
            <Volume2 className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onExit}>
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">Pairs found: {matchCount}/{pairCount} • Moves: {moves}</p>

      {feedback && (
        <div className="text-lg font-semibold text-primary animate-scale-in">{feedback}</div>
      )}

      <div className="grid grid-cols-4 gap-3 w-full max-w-md">
        {cards.map(card => (
          <button
            key={card.id}
            onClick={() => handleFlip(card.id)}
            disabled={card.flipped || card.matched || locked}
            className={`aspect-square rounded-2xl text-4xl flex items-center justify-center border-2 transition-all duration-300 ${
              card.matched
                ? 'bg-success/20 border-success scale-95 opacity-70'
                : card.flipped
                ? 'bg-primary/10 border-primary scale-105 shadow-lg'
                : 'bg-card border-border hover:border-primary/50 hover:shadow-md active:scale-95'
            }`}
            style={{ minHeight: '80px' }}
          >
            {card.flipped || card.matched ? card.emoji : '❓'}
          </button>
        ))}
      </div>

      <div className="flex gap-2 mt-2">
        <Button variant="outline" onClick={() => { initGame(); onSpeak('New game!'); }} className="rounded-xl">
          <RotateCcw className="w-4 h-4 mr-1" /> Restart
        </Button>
      </div>
    </div>
  );
};

export default MemoryMatchGame;

