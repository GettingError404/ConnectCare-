'use client';

import { createContext, useContext, useEffect, useState } from 'react';

const SocketContext = createContext<WebSocket | null>(null);

export function SocketProvider({ children }: { children: React.ReactNode }) {
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let ws: WebSocket | null = null;

    const connect = () => {
      const token = window.localStorage.getItem('access_token');
      const tenantId = window.localStorage.getItem('tenant_id') || process.env.NEXT_PUBLIC_TENANT_ID;
      if (!token || !tenantId) {
        ws?.close();
        ws = null;
        setSocket(null);
        return;
      }

      const baseUrl = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://127.0.0.1:8000';
      const url = new URL('/api/v1/ws/alerts', baseUrl);
      url.searchParams.set('token', token);
      url.searchParams.set('tenant_id', tenantId);

      ws?.close();
      ws = new WebSocket(url.toString());
      setSocket(ws);
    };

    const handleAuthChange = () => connect();

    connect();
    window.addEventListener('cc-auth-changed', handleAuthChange as EventListener);

    return () => {
      window.removeEventListener('cc-auth-changed', handleAuthChange as EventListener);
      ws?.close();
      setSocket(null);
    };
  }, []);

  return <SocketContext.Provider value={socket}>{children}</SocketContext.Provider>;
}

export function useSocket() {
  return useContext(SocketContext);
}
