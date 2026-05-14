'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Mic, MicOff, Volume2, X, RotateCcw, CheckCircle2, Send, Loader2 } from 'lucide-react';
import { useSpeechRecognition } from '@/hooks/useSpeech';

interface WordClue {
  word: string;
  clue: string;
  letters: string[];
}

const WORD_CLUES: WordClue[] = [
  { word: 'SUN', clue: 'It shines in the sky during the day', letters: ['S', 'U', 'N'] },
  { word: 'CAT', clue: 'A small furry pet that purrs', letters: ['C', 'A', 'T'] },
  { word: 'TREE', clue: 'It has leaves and grows in the ground', letters: ['T', 'R', 'E', 'E'] },
  { word: 'FISH', clue: 'It swims in the water', letters: ['F', 'I', 'S', 'H'] },
  { word: 'MOON', clue: 'You see it at night in the sky', letters: ['M', 'O', 'O', 'N'] },
  { word: 'BIRD', clue: 'It has wings and can fly', letters: ['B', 'I', 'R', 'D'] },
  { word: 'ROSE', clue: 'A beautiful red flower', letters: ['R', 'O', 'S', 'E'] },
  { word: 'CAKE', clue: 'A sweet treat for birthdays', letters: ['C', 'A', 'K', 'E'] },
  { word: 'RAIN', clue: 'Water falling from clouds', letters: ['R', 'A', 'I', 'N'] },
  { word: 'LOVE', clue: 'The strongest feeling in the world', letters: ['L', 'O', 'V', 'E'] },
];

interface WordClueGameProps {
  onExit: () => void;
  onSpeak: (text: string) => void;
}

type MicState = 'idle' | 'listening' | 'processing' | 'error';

const WordClueGame: React.FC<WordClueGameProps> = ({ onExit, onSpeak }) => {
  const [puzzles, setPuzzles] = useState<WordClue[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [revealedLetters, setRevealedLetters] = useState<boolean[]>([]);
  const [solved, setSolved] = useState(false);
  const [score, setScore] = useState(0);
  const [gameOver, setGameOver] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [answerInput, setAnswerInput] = useState('');
  const [micState, setMicState] = useState<MicState>('idle');
  const totalPuzzles = 5;

  const currentRef = useRef<WordClue | null>(null);
  const solvedRef = useRef(false);

  const {
    isListening, transcript, error: speechError,
    start: startStt, stop: stopStt, supported: sttSupported,
  } = useSpeechRecognition({
    onResult: (text) => {
      setMicState('processing');
      setAnswerInput(text);
      // Auto-submit voice answer
      setTimeout(() => {
        checkAnswer(text);
        setMicState('idle');
      }, 250);
    },
    onEnd: () => {
      setMicState((s) => (s === 'listening' ? 'idle' : s));
    },
    silenceTimeout: 1200,
  });

  useEffect(() => {
    if (speechError) setMicState('error');
  }, [speechError]);

  const initGame = useCallback(() => {
    const shuffled = [...WORD_CLUES].sort(() => Math.random() - 0.5).slice(0, totalPuzzles);
    setPuzzles(shuffled);
    setCurrentIndex(0);
    setRevealedLetters(new Array(shuffled[0]?.letters.length || 0).fill(false));
    setSolved(false);
    solvedRef.current = false;
    currentRef.current = shuffled[0] || null;
    setScore(0);
    setGameOver(false);
    setFeedback('');
    setAnswerInput('');
  }, []);

  useEffect(() => {
    initGame();
    setTimeout(() => onSpeak('Listen to the clue and say or type the word.'), 200);
    return () => { stopStt(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = puzzles[currentIndex];
  useEffect(() => { currentRef.current = current || null; }, [current]);
  useEffect(() => { solvedRef.current = solved; }, [solved]);

  const checkAnswer = useCallback((answer: string) => {
    const cur = currentRef.current;
    if (!cur || solvedRef.current) return;
    const lower = answer.toLowerCase().trim().replace(/[^a-z]/g, '');
    if (!lower) {
      setFeedback('Please say or type a word.');
      return;
    }
    if (lower === cur.word.toLowerCase()) {
      setSolved(true);
      solvedRef.current = true;
      setRevealedLetters(new Array(cur.letters.length).fill(true));
      setScore(s => s + 1);
      const msgs = ['Correct! Well done!', "That's right! Great job!", 'Perfect! You got it!'];
      const msg = msgs[Math.floor(Math.random() * msgs.length)];
      setFeedback('✅ ' + msg);
      onSpeak(msg);
    } else {
      setRevealedLetters(prev => {
        const next = [...prev];
        const hidden = next.findIndex(v => !v);
        if (hidden >= 0) next[hidden] = true;
        return next;
      });
      setFeedback(`❌ Not quite — try again. You said: "${answer}"`);
      onSpeak('Not quite. Try again.');
    }
  }, [onSpeak]);

  const nextPuzzle = () => {
    const next = currentIndex + 1;
    if (next >= totalPuzzles) {
      setGameOver(true);
      onSpeak(`Game over! You solved ${score} out of ${totalPuzzles} words.`);
      return;
    }
    setCurrentIndex(next);
    const p = puzzles[next];
    currentRef.current = p;
    setRevealedLetters(new Array(p.letters.length).fill(false));
    setSolved(false);
    solvedRef.current = false;
    setFeedback('');
    setAnswerInput('');
    setTimeout(() => onSpeak(p.clue), 150);
  };

  const handleSubmit = () => {
    if (!answerInput.trim()) return;
    checkAnswer(answerInput);
  };

  const toggleMic = () => {
    if (!sttSupported) {
      setMicState('error');
      setFeedback('Microphone is not supported in this browser. Please type your answer.');
      return;
    }
    if (isListening) {
      stopStt();
      setMicState('idle');
    } else {
      setMicState('listening');
      setFeedback('');
      startStt();
    }
  };

  // External voice command bridge
  useEffect(() => {
    type WindowWithWordClueCommand = Window & {
      __wordClueCommand?: (command: string) => void;
    };

    (window as WindowWithWordClueCommand).__wordClueCommand = (command: string) => {
      const lower = command.toLowerCase().trim();
      if (/repeat|instruction|help/.test(lower)) {
        if (currentRef.current) onSpeak(currentRef.current.clue);
      } else if (/restart|new game|again/.test(lower)) {
        initGame();
        onSpeak('New word game! Listen to the clue and say the word.');
      } else if (/exit|quit|stop|back/.test(lower)) {
        onExit();
      } else if (/skip|pass|next/.test(lower)) {
        if (!solvedRef.current && currentRef.current) {
          setRevealedLetters(new Array(currentRef.current.letters.length).fill(true));
          setSolved(true);
          solvedRef.current = true;
          setFeedback(`The word was: ${currentRef.current.word}`);
          onSpeak(`The word was ${currentRef.current.word}`);
        } else {
          nextPuzzle();
        }
      } else {
        checkAnswer(command);
      }
    };

    return () => {
      delete (window as WindowWithWordClueCommand).__wordClueCommand;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puzzles, currentIndex]);


  if (gameOver) {
    return (
      <div className="flex flex-col items-center justify-center gap-6 p-8 animate-fade-in">
        <div className="w-20 h-20 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-foreground">Great job!</h2>
          <p className="text-muted-foreground mt-1">You solved {score} out of {totalPuzzles} words.</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={() => { initGame(); onSpeak('New game started!'); }} size="lg" className="text-base px-6 py-5 rounded-xl">
            <RotateCcw className="w-4 h-4 mr-2" /> Play Again
          </Button>
          <Button onClick={onExit} variant="outline" size="lg" className="text-base px-6 py-5 rounded-xl">
            <X className="w-4 h-4 mr-2" /> Exit
          </Button>
        </div>
      </div>
    );
  }

  if (!current) return null;

  const micLabel: Record<MicState, string> = {
    idle: sttSupported ? 'Tap mic & say the word' : 'Mic unavailable',
    listening: 'Listening… speak now',
    processing: 'Processing your answer…',
    error: speechError || 'Mic error — type instead',
  };

  return (
    <div className="flex flex-col items-center gap-4 p-4 max-w-xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between w-full">
        <h2 className="font-heading text-xl font-semibold text-foreground">Word Clue</h2>
        <div className="flex gap-1">
          <Button variant="ghost" size="icon" onClick={() => onSpeak(current.clue)} aria-label="Repeat clue">
            <Volume2 className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onExit} aria-label="Exit">
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>Word {currentIndex + 1} / {totalPuzzles}</span>
        <span>·</span>
        <span>Score: {score}</span>
      </div>

      {/* Clue card */}
      <div className="w-full rounded-2xl bg-primary/5 border border-primary/15 p-5 text-center">
        <p className="text-xs uppercase tracking-wide text-primary/70 font-semibold mb-1">Clue</p>
        <p className="text-base md:text-lg font-medium text-foreground leading-relaxed">{current.clue}</p>
      </div>

      {/* Letter boxes */}
      <div className="flex gap-2.5 justify-center flex-wrap">
        {current.letters.map((letter, i) => (
          <div
            key={i}
            className={`w-12 h-14 md:w-14 md:h-16 rounded-xl border-2 flex items-center justify-center text-2xl font-bold transition-all duration-300 ${
              revealedLetters[i]
                ? 'bg-primary/10 border-primary/40 text-primary'
                : 'bg-muted/40 border-border text-muted-foreground/40'
            }`}
          >
            {revealedLetters[i] ? letter : '·'}
          </div>
        ))}
      </div>

      {feedback && (
        <p className={`text-sm font-medium animate-fade-in text-center ${solved ? 'text-success' : feedback.startsWith('❌') ? 'text-warning' : 'text-muted-foreground'}`}>
          {feedback}
        </p>
      )}

      {!solved ? (
        <div className="w-full space-y-3">
          {/* Answer input + submit */}
          <div className="flex gap-2">
            <Input
              value={answerInput}
              onChange={(e) => setAnswerInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="Type your answer…"
              className="text-base h-12 rounded-xl"
              aria-label="Your answer"
            />
            <Button onClick={handleSubmit} size="lg" className="h-12 rounded-xl px-5" disabled={!answerInput.trim()}>
              <Send className="w-4 h-4 mr-1.5" /> Check
            </Button>
          </div>

          {/* Mic control with states */}
          <div className="flex items-center gap-3">
            <button
              onClick={toggleMic}
              className={`flex-1 h-14 rounded-xl font-semibold flex items-center justify-center gap-2.5 transition-all border ${
                micState === 'listening'
                  ? 'bg-destructive text-destructive-foreground border-destructive shadow-lg'
                  : micState === 'processing'
                  ? 'bg-info/10 text-info border-info/30'
                  : micState === 'error'
                  ? 'bg-warning/10 text-warning border-warning/30'
                  : 'bg-card text-foreground border-border hover:bg-muted'
              }`}
              disabled={micState === 'processing'}
            >
              {micState === 'listening' ? <Mic className="w-5 h-5 animate-pulse" /> :
               micState === 'processing' ? <Loader2 className="w-5 h-5 animate-spin" /> :
               micState === 'error' ? <MicOff className="w-5 h-5" /> :
               <Mic className="w-5 h-5" />}
              <span className="text-sm">{micLabel[micState]}</span>
            </button>
          </div>

          {transcript && micState === 'listening' && (
            <p className="text-xs text-muted-foreground italic text-center">Heard: "{transcript}"</p>
          )}
        </div>
      ) : (
        <Button onClick={nextPuzzle} size="lg" className="w-full h-14 rounded-xl gap-2 text-base">
          <CheckCircle2 className="w-5 h-5" />
          {currentIndex + 1 < totalPuzzles ? 'Next Word' : 'See Results'}
        </Button>
      )}
    </div>
  );
};

export default WordClueGame;

