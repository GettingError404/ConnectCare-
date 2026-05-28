import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiStartConversation, apiVoiceWSUrl } from '@/services/voiceApi';
import { buildVoiceEvent, buildVoiceSocketUrlWithAuth, parseVoiceServerEvent } from '@/services/websocket';
import { useAudioPlayer } from './useAudioPlayer';
import {
  VoiceAgentResponsePayload,
  VoiceConnectionStatus,
  VoiceErrorPayload,
  VoiceServerEvent,
  VoiceTranscriptionPayload,
  VoiceTTSPayload,
} from '@/types/voice';

export type UseVoiceSocketOptions = {
  onTranscript?: (payload: VoiceTranscriptionPayload) => void;
  onAgentChunk?: (payload: VoiceAgentResponsePayload) => void;
  onAgentFinal?: (payload: VoiceAgentResponsePayload) => void;
  onConnectionStatus?: (status: VoiceConnectionStatus) => void;
  onError?: (payload: VoiceErrorPayload) => void;
};

export function useVoiceSocket(options: UseVoiceSocketOptions = {}) {
  const [status, setStatus] = useState<VoiceConnectionStatus>('disconnected');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [assistantDraft, setAssistantDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isThinking, setIsThinking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(1000);
  const reconnectTimerRef = useRef<number | null>(null);
  const audioPlayer = useAudioPlayer();

  const saveConversationState = useCallback((cid: string, sid: string) => {
    setConversationId(cid);
    setSessionId(sid);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('conversation_id', cid);
      window.localStorage.setItem('session_id', sid);
    }
  }, []);

  const setStatusSafe = useCallback((value: VoiceConnectionStatus) => {
    setStatus(value);
    options.onConnectionStatus?.(value);
  }, [options]);

  const sendEvent = useCallback(<Payload extends object>(type: string, payload: Payload) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const event = buildVoiceEvent(type, conversationId, sessionId, payload);
    ws.send(JSON.stringify(event));
  }, [conversationId, sessionId]);

  const handleServerEvent = useCallback((event: VoiceServerEvent) => {
    const { type, payload } = event;

    if (type === 'transcription') {
      const data = payload as VoiceTranscriptionPayload;
      setTranscript(data.text);
      options.onTranscript?.(data);
      return;
    }

    if (type === 'agent_thinking') {
      setIsThinking(true);
      setAssistantDraft('');
      return;
    }

    if (type === 'agent_response') {
      const data = payload as VoiceAgentResponsePayload;
      setAssistantDraft((previous) => (data.is_final ? previous : `${previous}${data.content}`));
      if (data.is_final) {
        setIsThinking(false);
        setAssistantDraft(data.content);
        options.onAgentFinal?.(data);
        setTimeout(() => setAssistantDraft(''), 200);
      } else {
        options.onAgentChunk?.(data);
      }
      return;
    }

    if (type === 'tts_audio_chunk') {
      const chunk = payload as VoiceTTSPayload;
      if (chunk.audio_b64) {
        audioPlayer.playBase64Audio(chunk.audio_b64).catch(() => null);
      }
      return;
    }

    if (type === 'conversation_started') {
      const data = payload as { conversation_id: string; session_id: string };
      saveConversationState(data.conversation_id, data.session_id);
      return;
    }

    if (type === 'error') {
      const data = payload as VoiceErrorPayload;
      setError(data.message);
      options.onError?.(data);
      return;
    }

    if (type === 'pong') {
      return;
    }
  }, [audioPlayer, options, saveConversationState]);

  const cleanupWebsocket = useCallback(() => {
    const ws = wsRef.current;
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onclose = null;
      ws.onerror = null;
      try { ws.close(); } catch {
        // ignore
      }
      wsRef.current = null;
    }
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (typeof window === 'undefined') return;
    if (status === 'connecting' || status === 'connected') return;

    setError(null);
    setStatusSafe('connecting');

    let cid = conversationId;
    let sid = sessionId;
    if (!cid || !sid) {
      try {
        const response = await apiStartConversation();
        cid = response.conversation_id;
        sid = response.session_id;
        if (cid && sid) {
          saveConversationState(cid, sid);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unable to start voice session';
        setError(message);
        setStatusSafe('disconnected');
        return;
      }
    }

    const url = buildVoiceSocketUrlWithAuth();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectRef.current = 1000;
      setStatusSafe('connected');
      sendEvent('start_conversation', { title: 'Voice session initialized' });
    };

    ws.onmessage = (raw) => {
      const event = parseVoiceServerEvent(raw.data);
      if (event) handleServerEvent(event);
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      setStatusSafe('disconnected');
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = window.setTimeout(() => {
        setStatusSafe('reconnecting');
        connect();
      }, reconnectRef.current);
      reconnectRef.current = Math.min(reconnectRef.current * 1.5, 60000);
    };
  }, [conversationId, handleServerEvent, saveConversationState, sendEvent, sessionId, setStatusSafe, status]);

  const disconnect = useCallback(() => {
    cleanupWebsocket();
    setStatusSafe('disconnected');
  }, [cleanupWebsocket, setStatusSafe]);

  const sendAudioChunk = useCallback((audioB64: string) => {
    sendEvent('user_audio_chunk', { audio_b64: audioB64 });
  }, [sendEvent]);

  const sendUserMessage = useCallback((text: string) => {
    sendEvent('user_message', { text });
  }, [sendEvent]);

  const stopConversation = useCallback(() => {
    sendEvent('stop_conversation', {});
  }, [sendEvent]);

  const ping = useCallback(() => {
    sendEvent('ping', {});
  }, [sendEvent]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    connect();
    return () => {
      cleanupWebsocket();
    };
  }, [connect, cleanupWebsocket]);

  const connectionSummary = useMemo(() => ({
    status,
    conversationId,
    sessionId,
    transcript,
    assistantDraft,
    error,
    isThinking,
  }), [assistantDraft, conversationId, error, isThinking, sessionId, status, transcript]);

  return {
    ...connectionSummary,
    connect,
    disconnect,
    sendAudioChunk,
    sendUserMessage,
    stopConversation,
    ping,
    audioPlayer,
  };
}
