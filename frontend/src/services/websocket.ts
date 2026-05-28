import { getAccessToken } from '@/lib/api/client';
import { VoiceClientEvent, VoiceServerEvent } from '@/types/voice';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? (typeof window !== 'undefined' ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}` : 'ws://127.0.0.1:8000');

export function getVoiceSocketUrl() {
  return `${WS_BASE}/api/v1/voice/ws`;
}

export function buildVoiceEvent<T extends object>(
  type: string,
  conversation_id: string | null,
  session_id: string | null,
  payload: T,
): VoiceClientEvent<T> {
  return { type, conversation_id, session_id, payload } as VoiceClientEvent<T>;
}

export function getVoiceSocketToken() {
  return getAccessToken();
}

export function buildVoiceSocketUrlWithAuth() {
  const token = getVoiceSocketToken();
  const tenantId = typeof window !== 'undefined' ? window.localStorage.getItem('tenant_id') : null;
  const url = new URL(getVoiceSocketUrl());
  if (token) url.searchParams.set('token', token);
  if (tenantId) url.searchParams.set('tenant_id', tenantId);
  return url.toString();
}

export function parseVoiceServerEvent(data: string): VoiceServerEvent | null {
  try {
    return JSON.parse(data) as VoiceServerEvent;
  } catch {
    return null;
  }
}
