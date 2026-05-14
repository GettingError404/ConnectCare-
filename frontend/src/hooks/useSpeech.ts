import { useCallback, useEffect, useRef, useState } from 'react';

interface UseSpeechOptions {
  onResult?: (text: string) => void;
  onEnd?: () => void;
  continuous?: boolean;
  silenceTimeout?: number;
}

export function useSpeechRecognition(options: UseSpeechOptions = {}) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  type SpeechRecognitionLike = {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    onstart?: () => void;
    onresult?: (event: unknown) => void;
    onerror?: (event: unknown) => void;
    onend?: () => void;
    start: () => void;
    stop: () => void;
  };

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const supported = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    setIsListening(false);
  }, []);

  const start = useCallback(() => {
    if (!supported) { setError('Speech recognition not supported'); return; }
    setError(null);
    setTranscript('');

    const SpeechRecognition = (window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    }).SpeechRecognition ||
      (window as unknown as {
        SpeechRecognition?: new () => SpeechRecognitionLike;
        webkitSpeechRecognition?: new () => SpeechRecognitionLike;
      }).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Speech recognition not supported');
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = options.continuous ?? false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: unknown) => {
      type SpeechRecognitionEventLike = {
        results: Array<{
          isFinal: boolean;
          0: { transcript: string };
        }>;
      };

      const ev = event as SpeechRecognitionEventLike;

      let final = '';
      let interim = '';
      for (let i = 0; i < ev.results.length; i++) {
        if (ev.results[i].isFinal) final += ev.results[i][0].transcript;
        else interim += ev.results[i][0].transcript;
      }
      const text = final || interim;
      setTranscript(text);


      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (final && options.onResult) {
        silenceTimerRef.current = setTimeout(() => {
          options.onResult?.(final.trim());
          stop();
          options.onEnd?.();
        }, options.silenceTimeout ?? 1500);
      }
    };
    recognition.onerror = (e: unknown) => {
      type SpeechErrorLike = { error?: string };
      const err = e as SpeechErrorLike;
      if (err.error !== 'aborted' && err.error) setError(err.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [supported, options.continuous, options.silenceTimeout, stop]);

  useEffect(() => () => { stop(); }, [stop]);

  return { isListening, transcript, error, start, stop, supported };
}

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const speak = useCallback((text: string, onEnd?: () => void) => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.volume = 1;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => { setIsSpeaking(false); onEnd?.(); };
    utterance.onerror = () => { setIsSpeaking(false); onEnd?.(); };
    window.speechSynthesis.speak(utterance);
  }, [supported]);

  const cancel = useCallback(() => {
    if (supported) window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, [supported]);

  return { speak, cancel, isSpeaking, supported };
}
