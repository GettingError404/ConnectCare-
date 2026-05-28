import { useCallback, useEffect, useRef, useState } from 'react';

function base64ToArrayBuffer(base64: string) {
  const binary = atob(base64);
  const len = binary.length;
  const buffer = new ArrayBuffer(len);
  const view = new Uint8Array(buffer);
  for (let i = 0; i < len; i += 1) {
    view[i] = binary.charCodeAt(i);
  }
  return buffer;
}

export function useAudioPlayer() {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playQueueTimeRef = useRef<number>(0);
  const sourceNodesRef = useRef<AudioBufferSourceNode[]>([]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const ctx = new AudioContext();
    audioContextRef.current = ctx;
    return () => {
      sourceNodesRef.current.forEach((source) => {
        try {
          source.stop();
        } catch {
          // ignore
        }
      });
      sourceNodesRef.current = [];
      ctx.close().catch(() => null);
    };
  }, []);

  const stop = useCallback(() => {
    sourceNodesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {
        // ignore
      }
    });
    sourceNodesRef.current = [];
    playQueueTimeRef.current = 0;
    setIsPlaying(false);
  }, []);

  const ensureContext = useCallback(async () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }
    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
    return ctx;
  }, []);

  const playBase64Audio = useCallback(async (base64: string) => {
    try {
      const ctx = await ensureContext();
      const buffer = base64ToArrayBuffer(base64);
      const decoded = await ctx.decodeAudioData(buffer.slice(0));
      const source = ctx.createBufferSource();
      source.buffer = decoded;
      source.connect(ctx.destination);
      const startAt = Math.max(ctx.currentTime + 0.05, playQueueTimeRef.current || ctx.currentTime + 0.05);
      source.start(startAt);
      source.onended = () => {
        sourceNodesRef.current = sourceNodesRef.current.filter((node) => node !== source);
        if (!sourceNodesRef.current.length) {
          setIsPlaying(false);
          playQueueTimeRef.current = 0;
        }
      };
      sourceNodesRef.current.push(source);
      playQueueTimeRef.current = startAt + decoded.duration;
      setIsPlaying(true);
      return decoded.duration;
    } catch (error) {
      console.error('Audio playback failed', error);
      throw error;
    }
  }, [ensureContext]);

  return {
    isPlaying,
    playBase64Audio,
    stop,
  };
}
