'use client';

import { createContext, useContext, useEffect, useRef, useState } from 'react';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

type OutgoingUserMessage = {
  type: 'user_message';
  conversation_id: string;
  message_id: string;
  content: string;
  sequence_number: number;
  timestamp: string;
};

type SocketContextValue = {
  sendUserMessage: (payload: Omit<OutgoingUserMessage, 'type'>) => void;
  sendAck: (message_id: string) => void;
  requestReplay: (opts?: { reconnect_token?: string }) => void;
  connectionStatus: ConnectionStatus;
  conversationId: string | null;
  setConversationId: (id: string | null) => void;
};

const SocketContext = createContext<SocketContextValue | null>(null);

function makeMessageId() {
  if (typeof crypto !== 'undefined' && (crypto as any).randomUUID) return (crypto as any).randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function SocketProvider({ children }: { children: React.ReactNode }) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [conversationId, setConversationIdState] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem('conversation_id');
  });

  const wsRef = useRef<WebSocket | null>(null);
  const pendingAcks = useRef<Record<string, any>>({});
  const sequenceRef = useRef<number>(0);
  const reconnectTokenRef = useRef<string | null>(null);
  const heartbeatRef = useRef<number | null>(null);
  const backoffRef = useRef<number>(1000);

  const baseUrl = typeof window !== 'undefined' ? process.env.NEXT_PUBLIC_WS_URL ?? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}` : 'ws://127.0.0.1:8000';

  const setConversationId = (id: string | null) => {
    setConversationIdState(id);
    if (typeof window !== 'undefined') {
      if (id) window.localStorage.setItem('conversation_id', id);
      else window.localStorage.removeItem('conversation_id');
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let shouldStop = false;

    const connect = () => {
      const token = window.localStorage.getItem('access_token');
      const sessionId = window.localStorage.getItem('session_id') || '';
      const conversation_id = conversationId ?? '';
      if (!token) {
        setConnectionStatus('disconnected');
        return;
      }

      setConnectionStatus('connecting');

      const url = new URL('/ws/stream/v2', baseUrl);
      // gateway_v2 expects `token` query param for JWT
      url.searchParams.set('token', token);
      // legacy/backwards-compatible param
      url.searchParams.set('access_token', token);
      if (conversation_id) url.searchParams.set('conversation_id', conversation_id);
      if (sessionId) url.searchParams.set('session_id', sessionId);
      if (reconnectTokenRef.current) url.searchParams.set('reconnect_token', reconnectTokenRef.current);

      try {
        wsRef.current?.close();
      } catch (e) {}

      const ws = new WebSocket(url.toString(), ['cc-v2']);
      wsRef.current = ws;

      ws.onopen = () => {
        backoffRef.current = 1000;
        setConnectionStatus(reconnectTokenRef.current ? 'reconnecting' : 'connected');
        // start heartbeat
        if (heartbeatRef.current) window.clearInterval(heartbeatRef.current);
        heartbeatRef.current = window.setInterval(() => {
          try {
            ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));
          } catch (e) {}
        }, 25000);
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          // handle v2 gateway message types
          if (msg.type === 'auth_success') {
            window.dispatchEvent(new CustomEvent('cc-auth-success', { detail: msg }));
          } else if (msg.type === 'message_chunk' || msg.type === 'replay_chunk') {
            // deliver to app
            window.dispatchEvent(new CustomEvent('cc-message-chunk', { detail: msg }));
            // acknowledge chunk
            const ack = {
              type: 'message_ack',
              message_id: msg.message_id,
              sequence_no: msg.sequence_no ?? msg.seq ?? null,
              last_chunk_no: msg.chunk_index ?? null,
              conversation_id: msg.conversation_id ?? msg.conversation_id,
            };
            try { ws.send(JSON.stringify(ack)); } catch (e) {}
          } else if (msg.type === 'message_complete') {
            window.dispatchEvent(new CustomEvent('cc-message-complete', { detail: msg }));
          } else if (msg.type === 'replay_start' || msg.type === 'replay_complete') {
            window.dispatchEvent(new CustomEvent(`cc-${msg.type}`, { detail: msg }));
          } else if (msg.type === 'heartbeat' || msg.type === 'pong') {
            // server heartbeat
          } else if (msg.type === 'error') {
            window.dispatchEvent(new CustomEvent('cc-socket-error', { detail: msg }));
          } else {
            window.dispatchEvent(new CustomEvent('cc-socket-message', { detail: msg }));
          }
        } catch (e) {}
      };

      ws.onclose = () => {
        setConnectionStatus('disconnected');
        if (heartbeatRef.current) window.clearInterval(heartbeatRef.current);
        if (shouldStop) return;
        // reconnect with backoff
        setTimeout(() => {
          backoffRef.current = Math.min(60000, backoffRef.current * 1.5);
          connect();
        }, backoffRef.current);
      };

      ws.onerror = (e) => {
        window.dispatchEvent(new CustomEvent('cc-socket-error', { detail: e }));
      };
    };

    connect();

    const handleAuthChange = () => {
      // re-init connection when auth changes
      reconnectTokenRef.current = null;
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (e) {}
      }
      connect();
    };

    window.addEventListener('cc-auth-changed', handleAuthChange as EventListener);

    return () => {
      shouldStop = true;
      window.removeEventListener('cc-auth-changed', handleAuthChange as EventListener);
      if (heartbeatRef.current) window.clearInterval(heartbeatRef.current);
      try { wsRef.current?.close(); } catch (e) {}
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const sendUserMessage = (payload: Omit<OutgoingUserMessage, 'type'>) => {
    const ws = wsRef.current;
    const message: OutgoingUserMessage = {
      type: 'user_message',
      ...payload,
    };

    try {
      // track pending ack
      pendingAcks.current[message.message_id] = { message, ts: Date.now() };
      ws?.send(JSON.stringify(message));
    } catch (e) {
      // store locally for replay
      pendingAcks.current[message.message_id] = { message, ts: Date.now(), unsent: true };
    }
  };

  const sendAck = (message_id: string, sequence_no?: number, last_chunk_no?: number, conversation_id?: string) => {
    try {
      wsRef.current?.send(JSON.stringify({
        type: 'message_ack',
        message_id,
        sequence_no: sequence_no ?? null,
        last_chunk_no: last_chunk_no ?? null,
        conversation_id: conversation_id ?? conversationId,
      }));
    } catch (e) {}
  };

  const requestReplay = (opts?: { reconnect_token?: string }) => {
    try {
      const ws = wsRef.current;
      const lastSeq = sequenceRef.current;
      const payload = {
          type: 'reconnect',
          conversation_id: conversationId,
          resume_token: opts?.reconnect_token ?? reconnectTokenRef.current,
          last_sequence_no: lastSeq,
        } as any;
      ws?.send(JSON.stringify(payload));
    } catch (e) {}
  };

  useEffect(() => {
    // resend unsent pending acks on reconnect
    const onReconnectAck = () => {
      try {
        const ws = wsRef.current;
        Object.values(pendingAcks.current).forEach((item: any) => {
          if (item.unsent) {
            ws?.send(JSON.stringify(item.message));
            delete item.unsent;
          }
        });
      } catch (e) {}
    };

    window.addEventListener('cc-reconnect-ack', onReconnectAck as EventListener);
    return () => window.removeEventListener('cc-reconnect-ack', onReconnectAck as EventListener);
  }, []);

  return (
    <SocketContext.Provider
      value={{
        sendUserMessage: (p) => sendUserMessage({ ...p, timestamp: new Date().toISOString() }),
        sendAck,
        requestReplay,
        connectionStatus,
        conversationId,
        setConversationId,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const ctx = useContext(SocketContext);
  if (!ctx) throw new Error('useSocket must be used within SocketProvider');
  return ctx;
}
