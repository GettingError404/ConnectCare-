import { useCallback, useEffect, useRef, useState } from 'react';
import { useSpeechRecognition, useSpeechSynthesis } from '@/hooks/useSpeech';
import { detectIntent, IntentResult } from '@/services/intentService';
import { useElderStore } from '@/store/elderStore';
import { useAuthStore } from '@/store/authStore';
import { ChatMessage } from '@/types';

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

interface UseVoiceEngineOptions {
  onNavigate?: (tab: string) => void;
  onCheckInStart?: () => void;
  autoStart?: boolean;
}

export function useVoiceEngine(options: UseVoiceEngineOptions = {}) {
  const { user } = useAuthStore();
  const store = useElderStore();
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [continuousMode, setContinuousMode] = useState(false);
  const continuousModeRef = useRef(false);
  const processingRef = useRef(false);

  const {
    addChatMessage, reminders, updateReminderStatus, addStars, addMoodEntry,
    toggleDevice, triggerEmergency, smartDevices, vitals, checkIn, updateCheckIn,
    completeCheckIn, familyContacts, initiateCall, cancelCall, endCall, callState,
    gameSession, startGame, answerGame, endGame,
    playMusic, toggleMusicPlayback, nextTrack, prevTrack, stopMusic,
  } = store;

  const restartListening = useCallback(() => {
    if (continuousModeRef.current && !processingRef.current) {
      setTimeout(() => {
        if (continuousModeRef.current) { startListening(); setVoiceState('listening'); }
      }, 800);
    }
  }, []);

  const handleVoiceResult = useCallback((text: string) => {
    if (processingRef.current) return;
    processingRef.current = true;
    processInput(text);
  }, []);

  const { isListening, transcript, error: speechError, start: startListening, stop: stopListening, supported: sttSupported } = useSpeechRecognition({
    onResult: handleVoiceResult,
    onEnd: () => { if (continuousModeRef.current && !processingRef.current) restartListening(); },
    silenceTimeout: 2500,
  });

  const { speak, isSpeaking, cancel: cancelSpeech, supported: ttsSupported } = useSpeechSynthesis();

  useEffect(() => {
    if (isListening) setVoiceState('listening');
    else if (isSpeaking) setVoiceState('speaking');
    else if (processingRef.current) setVoiceState('processing');
    else if (continuousModeRef.current) setVoiceState('listening');
    else setVoiceState('idle');
  }, [isListening, isSpeaking]);

  const executeAction = useCallback((result: IntentResult) => {
    const { action } = result;
    const data = result.data as Record<string, unknown> | undefined;


    // Navigation
    if (action === 'navigate_reminders' || action === 'show_reminders') options.onNavigate?.('reminders');
    else if (action === 'show_vitals' || action === 'navigate_health') options.onNavigate?.('vitals');
    else if (action === 'show_smart_home' || action === 'navigate_home') options.onNavigate?.('home');
    else if (action === 'navigate_companion' || action === 'navigate_talk') options.onNavigate?.('companion');
    else if (action === 'show_games' || action === 'navigate_games') options.onNavigate?.('games');
    else if (action === 'show_entertainment') options.onNavigate?.('companion');

    // Reminders
    if (action === 'mark_medicine_done') {
      const upcoming = reminders.find(r => r.status === 'upcoming' && r.type === 'medication');
      if (upcoming) { updateReminderStatus(upcoming.id, 'completed'); addStars(5, 'Medication taken'); }
    } else if (action === 'snooze_reminder') {
      const upcoming = reminders.find(r => r.status === 'upcoming');
      if (upcoming) updateReminderStatus(upcoming.id, 'snoozed');
    } else if (action === 'mark_all_reminders_done') {
      reminders.filter(r => r.status === 'upcoming').forEach(r => { updateReminderStatus(r.id, 'completed'); addStars(2, `${r.title} completed`); });
    }

    // Mood
    if (action === 'log_mood') {
      const moodMap: Record<string, string> = { positive: 'happy', negative: 'sad', risk: 'anxious' };
      const rawSentiment = (data as Record<string, unknown> | undefined)?.sentiment;
      const sentiment = typeof rawSentiment === 'string' ? rawSentiment : undefined;
      const mappedMood = moodMap[sentiment as keyof typeof moodMap] ?? 'neutral';
      const rawUserText = (data as Record<string, unknown> | undefined)?.userText;
      const rawTriggers = (data as Record<string, unknown> | undefined)?.triggers;
      const note = typeof rawUserText === 'string' ? rawUserText : 'Voice mood entry';
      const triggers = Array.isArray(rawTriggers) ? (rawTriggers as string[]) : undefined;

      addMoodEntry({
        id: `m-${Date.now()}`,
        mood: mappedMood as unknown as 'happy' | 'sad' | 'anxious' | 'neutral',
        score: sentiment === 'positive' ? 8 : sentiment === 'negative' ? 3 : 5,
        note,
        timestamp: new Date().toISOString(),
        sentiment: (typeof sentiment === 'string' ? sentiment : 'neutral') as
          | 'positive'
          | 'neutral'
          | 'negative'
          | 'risk',
        triggers,
      });

      addStars(3, 'Mood logged');
    }

    // Smart home
    if (action === 'toggle_lights') { const l = smartDevices.find(d => d.type === 'light'); if (l) toggleDevice(l.id); }
    else if (action === 'toggle_lock') { const l = smartDevices.find(d => d.type === 'lock'); if (l) toggleDevice(l.id); }
    else if (action === 'toggle_all_lights_on' || action === 'toggle_all_lights_off') { smartDevices.filter(d => d.type === 'light').forEach(d => toggleDevice(d.id)); }

    // Emergency
    if (action === 'trigger_sos' || action === 'trigger_sos_critical') {
      triggerEmergency('voice');
      if (action === 'trigger_sos_critical') {
        familyContacts.filter(c => c.isPrimary || c.relationship === 'Caregiver').forEach(c => {
          addChatMessage({ id: `msg-alert-${Date.now()}-${c.id}`, role: 'assistant', content: `🚨 Emergency alert sent to ${c.name} (${c.relationship})`, timestamp: new Date().toISOString(), tags: ['emergency', 'alert'] });
        });
      }
    }

    // Calls
    const rawContactId = (data as Record<string, unknown> | undefined)?.contactId;
    if (action === 'initiate_call' && rawContactId && typeof rawContactId === 'string') initiateCall(rawContactId);

    if (action === 'cancel_call') cancelCall();
    if (action === 'retry_call' && callState.contactId) initiateCall(callState.contactId);

    // Hydration
    if (action === 'mark_hydration') {
      const h = reminders.find(r => r.type === 'hydration' && r.status === 'upcoming');
      if (h) { updateReminderStatus(h.id, 'completed'); addStars(2, 'Hydration completed'); }
    }

    // Check-in
    if (action === 'start_checkin') options.onCheckInStart?.();
    if (action === 'start_exercise') addStars(5, 'Exercise started');

    // === GAMES ===
    const rawGameType = (data as Record<string, unknown> | undefined)?.gameType;
    if (action === 'start_game' && typeof rawGameType === 'string') {
      startGame(rawGameType as 'quiz' | 'memory' | 'word');
      addStars(2, 'Started a game');
    }

    if (action === 'end_game') endGame();

    // === MUSIC ===
    const rawGenre = (data as Record<string, unknown> | undefined)?.genre;
    if (action === 'play_music' && typeof rawGenre === 'string') {
      playMusic(rawGenre);
      addStars(2, 'Playing music');
    }

    if (action === 'toggle_music') toggleMusicPlayback();
    if (action === 'next_track') nextTrack();
    if (action === 'prev_track') prevTrack();
    if (action === 'stop_music') stopMusic();
  }, [reminders, smartDevices, familyContacts, callState, options.onNavigate, options.onCheckInStart]);

  const processInput = useCallback((text: string) => {
    setVoiceState('processing');
    const userMsg: ChatMessage = { id: `msg-${Date.now()}`, role: 'user', content: text, timestamp: new Date().toISOString() };
    addChatMessage(userMsg);

    const result = detectIntent(text, {
      reminders, name: user?.name?.split(' ')[0], vitals, checkIn, smartDevices, familyContacts, gameSession,
    });

    // Handle game answers specially
    if (result.action === 'game_answer' && (result.data as Record<string, unknown> | undefined)?.answer) {
      const answer = (result.data as Record<string, unknown>).answer as string;
      const skipped = Boolean((result.data as Record<string, unknown> | undefined)?.skipped);
      const gameResult = answerGame(skipped ? '' : answer);


      let responseText: string;
      if (skipped) {
        responseText = gameResult.correctAnswer
          ? `No worries! The answer was: ${gameResult.correctAnswer}. ${gameResult.done ? `Game over! Your final score: ${gameSession.score}/${gameSession.totalQuestions}. 🎉` : "Let's try the next one!"}`
          : "Skipped! Let's move on.";
      } else if (gameResult.correct) {
        responseText = `✅ Correct! Great job! ${gameResult.done ? `🎉 Game complete! Final score: ${gameSession.score + 1}/${gameSession.totalQuestions}! You earned ${(gameSession.score + 1) * 3} wellness stars!` : 'Here comes the next one!'}`;
        if (gameResult.done) addStars((gameSession.score + 1) * 3, 'Game completed');
      } else {
        responseText = `❌ Not quite! The answer was: ${gameResult.correctAnswer || 'unknown'}. ${gameResult.done ? `Game over! Your score: ${gameSession.score}/${gameSession.totalQuestions}. Well played! 🌟` : "Don't worry, let's try the next one!"}`;
        if (gameResult.done) addStars(Math.max(gameSession.score * 2, 1), 'Game completed');
      }

      const aiMsg: ChatMessage = { id: `msg-${Date.now() + 1}`, role: 'assistant', content: responseText, timestamp: new Date().toISOString(), intent: 'game_answer', tags: ['game'] };
      setTimeout(() => {
        addChatMessage(aiMsg);
        setVoiceState('speaking');
        if (ttsSupported) {
          speak(responseText, () => { processingRef.current = false; if (continuousModeRef.current) restartListening(); else setVoiceState('idle'); });
        } else { processingRef.current = false; if (continuousModeRef.current) restartListening(); else setVoiceState('idle'); }
      }, 300);
      return;
    }

    executeAction(result);

    const aiMsg: ChatMessage = { id: `msg-${Date.now() + 1}`, role: 'assistant', content: result.response, timestamp: new Date().toISOString(), intent: result.intent, tags: [result.intent] };
    setTimeout(() => {
      addChatMessage(aiMsg);
      setVoiceState('speaking');
      if (ttsSupported) {
        speak(result.response, () => { processingRef.current = false; if (continuousModeRef.current) restartListening(); else setVoiceState('idle'); });
      } else { processingRef.current = false; if (continuousModeRef.current) restartListening(); else setVoiceState('idle'); }
    }, 300);
  }, [reminders, user, vitals, checkIn, smartDevices, familyContacts, gameSession, ttsSupported]);

  const startContinuous = useCallback(() => { setContinuousMode(true); continuousModeRef.current = true; cancelSpeech(); processingRef.current = false; startListening(); setVoiceState('listening'); }, []);
  const stopContinuous = useCallback(() => { setContinuousMode(false); continuousModeRef.current = false; processingRef.current = false; stopListening(); cancelSpeech(); setVoiceState('idle'); }, []);
  const toggleContinuous = useCallback(() => { if (continuousModeRef.current) stopContinuous(); else startContinuous(); }, [startContinuous, stopContinuous]);

  const speakProactive = useCallback((text: string, addToChat = true) => {
    if (addToChat) addChatMessage({ id: `msg-${Date.now()}`, role: 'assistant', content: text, timestamp: new Date().toISOString(), tags: ['proactive'] });
    const wasContinuous = continuousModeRef.current;
    if (wasContinuous) stopListening();
    setVoiceState('speaking');
    speak(text, () => { if (wasContinuous) restartListening(); else setVoiceState('idle'); });
  }, []);

  const processTextInput = useCallback((text: string) => { processingRef.current = true; processInput(text); }, [processInput]);

  return {
    voiceState, continuousMode, isListening, isSpeaking, transcript, speechError,
    sttSupported, ttsSupported, startContinuous, stopContinuous, toggleContinuous,
    processTextInput, speakProactive, cancelSpeech,
  };
}

