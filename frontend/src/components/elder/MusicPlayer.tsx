'use client';
import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipForward, SkipBack, Volume2, VolumeX, Music, X } from 'lucide-react';
import { useElderStore } from '@/store/elderStore';

interface MusicPlayerProps {
  onVoiceCommand: (text: string) => void;
}

const MusicPlayer: React.FC<MusicPlayerProps> = ({ onVoiceCommand }) => {
  const { musicPlayer, toggleMusicPlayback, nextTrack, prevTrack, stopMusic } = useElderStore();
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (musicPlayer.status !== 'playing' || !musicPlayer.currentTrack) return;
    const interval = setInterval(() => {
      setProgress(prev => {
        const next = prev + 1;
        if (next >= musicPlayer.currentTrack!.duration) {
          nextTrack();
          return 0;
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [musicPlayer.status, musicPlayer.currentTrack?.id]);

  useEffect(() => {
    setProgress(0);
  }, [musicPlayer.currentTrack?.id]);

  if (!musicPlayer.currentTrack) return null;

  const track = musicPlayer.currentTrack;
  const duration = track.duration;
  const pct = (progress / duration) * 100;

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  const genreEmoji: Record<string, string> = {
    devotional: '🙏', classical: '🎻', oldies: '🎶', nature: '🌿', calm: '🧘', folk: '🎸',
  };

  return (
    <div className="w-full max-w-sm mx-auto bg-card rounded-2xl border border-border p-4 space-y-3 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl">
            {genreEmoji[track.genre] || '🎵'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-foreground truncate">{track.title}</p>
            <p className="text-xs text-muted-foreground truncate">{track.artist}</p>
          </div>
        </div>
        <button onClick={stopMusic} className="p-1.5 rounded-full hover:bg-muted transition-colors">
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full transition-all duration-1000" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>{formatTime(progress)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        <button onClick={prevTrack} className="p-2 rounded-full hover:bg-muted transition-colors">
          <SkipBack className="w-5 h-5 text-foreground" />
        </button>
        <button
          onClick={toggleMusicPlayback}
          className="p-3 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md"
        >
          {musicPlayer.status === 'playing' ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
        </button>
        <button onClick={nextTrack} className="p-2 rounded-full hover:bg-muted transition-colors">
          <SkipForward className="w-5 h-5 text-foreground" />
        </button>
      </div>

      {/* Queue info */}
      {musicPlayer.queue.length > 0 && (
        <p className="text-center text-[10px] text-muted-foreground">
          {musicPlayer.queue.length} more track{musicPlayer.queue.length > 1 ? 's' : ''} in queue •
          Say "next", "pause", or "stop music"
        </p>
      )}
    </div>
  );
};

export default MusicPlayer;


