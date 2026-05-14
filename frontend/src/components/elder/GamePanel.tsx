import React from 'react';
import { Brain, HelpCircle, Type, Trophy, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useElderStore } from '@/store/elderStore';

interface GamePanelProps {
  onVoiceCommand: (text: string) => void;
}

const GamePanel: React.FC<GamePanelProps> = ({ onVoiceCommand }) => {
  const { gameSession } = useElderStore();

  if (!gameSession || gameSession.status === 'idle') {
    return (
      <div className="w-full max-w-sm mx-auto space-y-3">
        <h3 className="text-center text-lg font-bold text-foreground">🎮 Choose a Game</h3>
        <div className="grid grid-cols-1 gap-3">
          {[
            { icon: <Brain className="w-6 h-6" />, label: 'Memory Game', command: 'play memory game', desc: 'Remember and match pairs', color: 'bg-primary/10 text-primary' },
            { icon: <HelpCircle className="w-6 h-6" />, label: 'Quiz Game', command: 'play quiz game', desc: 'Test your knowledge', color: 'bg-warning/10 text-warning' },
            { icon: <Type className="w-6 h-6" />, label: 'Word Puzzle', command: 'play word game', desc: 'Unscramble the letters', color: 'bg-info/10 text-info' },
          ].map(game => (
            <button
              key={game.label}
              onClick={() => onVoiceCommand(game.command)}
              className={`flex items-center gap-3 p-4 rounded-2xl ${game.color} border border-border/50 hover:scale-[1.02] active:scale-95 transition-all text-left`}
            >
              {game.icon}
              <div>
                <p className="font-semibold text-sm">{game.label}</p>
                <p className="text-xs opacity-70">{game.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Active game display
  const { type, currentQuestion, score, totalQuestions, status } = gameSession;

  if (status === 'completed') {
    return (
      <div className="w-full max-w-sm mx-auto text-center space-y-4 p-6 bg-card rounded-2xl border border-border">
        <Trophy className="w-12 h-12 text-warning mx-auto" />
        <h3 className="text-xl font-bold text-foreground">Game Over!</h3>
        <p className="text-3xl font-bold text-primary">{score} / {totalQuestions}</p>
        <p className="text-sm text-muted-foreground">
          {score === totalQuestions ? '🌟 Perfect score! Amazing!' :
           score >= totalQuestions * 0.7 ? '🎉 Great job! Well played!' :
           score >= totalQuestions * 0.4 ? '👍 Good effort! Keep practicing!' :
           '💪 Nice try! Want to play again?'}
        </p>
        <div className="flex gap-2 justify-center">
          <Button onClick={() => onVoiceCommand('play again')} className="gap-1">
            Play Again <ArrowRight className="w-4 h-4" />
          </Button>
          <Button variant="outline" onClick={() => onVoiceCommand('stop game')}>
            Done
          </Button>
        </div>
      </div>
    );
  }

  // Quiz game active
  if (type === 'quiz' && gameSession.quizData) {
    const q = gameSession.quizData;
    return (
      <div className="w-full max-w-sm mx-auto space-y-4 p-4 bg-card rounded-2xl border border-border">
        <div className="flex justify-between items-center">
          <span className="text-xs font-semibold text-muted-foreground">Question {currentQuestion + 1}/{totalQuestions}</span>
          <span className="text-xs font-bold text-primary">Score: {score} ⭐</span>
        </div>
        <p className="text-base font-semibold text-foreground leading-relaxed">{q.question}</p>
        <div className="grid grid-cols-1 gap-2">
          {q.options.map((opt, i) => (
            <button
              key={i}
              onClick={() => onVoiceCommand(opt)}
              className="text-left px-4 py-3 rounded-xl bg-muted hover:bg-primary/10 border border-border/50 text-sm font-medium transition-all hover:scale-[1.01] active:scale-95"
            >
              <span className="text-muted-foreground mr-2">{['A', 'B', 'C', 'D'][i]}.</span>
              {opt}
            </button>
          ))}
        </div>
        <p className="text-center text-xs text-muted-foreground">Say the answer or tap to select</p>
      </div>
    );
  }

  // Memory game active
  if (type === 'memory' && gameSession.memoryData) {
    const { sequence, revealed } = gameSession.memoryData;
    return (
      <div className="w-full max-w-sm mx-auto space-y-4 p-4 bg-card rounded-2xl border border-border">
        <div className="flex justify-between items-center">
          <span className="text-xs font-semibold text-muted-foreground">Round {currentQuestion + 1}/{totalQuestions}</span>
          <span className="text-xs font-bold text-primary">Score: {score} ⭐</span>
        </div>
        <p className="text-sm font-medium text-foreground text-center">
          {revealed
            ? `Remember this sequence: ${sequence.map(s => s.emoji).join(' ')}`
            : 'What was the sequence? Say the items in order!'}
        </p>
        <div className="flex justify-center gap-3 flex-wrap">
          {sequence.map((item, i) => (
            <div
              key={i}
              className={`w-14 h-14 rounded-xl flex items-center justify-center text-2xl border-2 transition-all ${
                revealed ? 'bg-primary/10 border-primary/30' : 'bg-muted border-border'
              }`}
            >
              {revealed ? item.emoji : '❓'}
            </div>
          ))}
        </div>
        <p className="text-center text-xs text-muted-foreground">
          {revealed ? 'Memorize the pattern...' : 'Say what you remember!'}
        </p>
      </div>
    );
  }

  // Word game active
  if (type === 'word' && gameSession.wordData) {
    const { scrambled, hint } = gameSession.wordData;
    return (
      <div className="w-full max-w-sm mx-auto space-y-4 p-4 bg-card rounded-2xl border border-border">
        <div className="flex justify-between items-center">
          <span className="text-xs font-semibold text-muted-foreground">Puzzle {currentQuestion + 1}/{totalQuestions}</span>
          <span className="text-xs font-bold text-primary">Score: {score} ⭐</span>
        </div>
        <div className="text-center space-y-2">
          <p className="text-sm text-muted-foreground">Unscramble this word:</p>
          <div className="flex justify-center gap-2">
            {scrambled.split('').map((letter, i) => (
              <div key={i} className="w-10 h-12 rounded-lg bg-primary/10 border-2 border-primary/30 flex items-center justify-center text-lg font-bold text-primary">
                {letter}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground italic">💡 Hint: {hint}</p>
        </div>
        <p className="text-center text-xs text-muted-foreground">Say your answer or type it below</p>
      </div>
    );
  }

  return null;
};

export default GamePanel;

