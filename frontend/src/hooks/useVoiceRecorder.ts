import { useCallback, useEffect, useRef, useState } from 'react';

type VoiceRecorderOptions = {
  onChunk: (chunk: string) => void;
  onError?: (error: string) => void;
  chunkDurationMs?: number;
};

function floatTo16BitPCM(output: DataView, offset: number, input: Float32Array) {
  for (let i = 0; i < input.length; i += 1, offset += 2) {
    let s = Math.max(-1, Math.min(1, input[i]));
    output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i += 1) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

function encodeWAV(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  floatTo16BitPCM(view, 44, samples);
  return buffer;
}

function base64Encode(buffer: ArrayBuffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const sub = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...sub);
  }
  return btoa(binary);
}

function downsampleBuffer(buffer: Float32Array, sampleRate: number, outSampleRate: number) {
  if (outSampleRate === sampleRate) return buffer;
  if (outSampleRate > sampleRate) {
    return buffer;
  }

  const sampleRateRatio = sampleRate / outSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      accum += buffer[i];
      count += 1;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

export function useVoiceRecorder(options: VoiceRecorderOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const scriptNodeRef = useRef<ScriptProcessorNode | null>(null);
  const bufferRef = useRef<Float32Array[]>([]);
  const lastChunkTimeRef = useRef<number>(0);

  const flushChunk = useCallback(() => {
    const audioContext = audioContextRef.current;
    const buffers = bufferRef.current;
    if (!audioContext || buffers.length === 0) return;
    const sampleRate = audioContext.sampleRate;
    const length = buffers.reduce((sum, buf) => sum + buf.length, 0);
    const merged = new Float32Array(length);
    let offset = 0;
    buffers.forEach((chunk) => {
      merged.set(chunk, offset);
      offset += chunk.length;
    });
    bufferRef.current = [];
    const downsampled = downsampleBuffer(merged, sampleRate, 16000);
    const wav = encodeWAV(downsampled, 16000);
    options.onChunk(base64Encode(wav));
  }, [options]);

  const start = useCallback(async () => {
    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      const message = 'Microphone capture not supported';
      setError(message);
      options.onError?.(message);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        const inputBuffer = event.inputBuffer.getChannelData(0);
        bufferRef.current.push(new Float32Array(inputBuffer));
        const now = performance.now();
        if (now - lastChunkTimeRef.current > (options.chunkDurationMs ?? 500)) {
          lastChunkTimeRef.current = now;
          flushChunk();
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      audioContextRef.current = audioContext;
      mediaStreamRef.current = stream;
      scriptNodeRef.current = processor;
      setIsRecording(true);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Microphone access denied';
      setError(message);
      options.onError?.(message);
    }
  }, [flushChunk, options]);

  const stop = useCallback(() => {
    if (scriptNodeRef.current) {
      scriptNodeRef.current.disconnect();
      scriptNodeRef.current.onaudioprocess = null;
      scriptNodeRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => null);
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    flushChunk();
    setIsRecording(false);
  }, [flushChunk]);

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    isRecording,
    error,
    start,
    stop,
  };
}
