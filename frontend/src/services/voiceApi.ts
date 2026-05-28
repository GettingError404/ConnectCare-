const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export async function apiStartConversation() {
  const res = await fetch(`${API_BASE}/api/v1/voice/start`, { method: 'POST' });
  return res.json();
}

export async function apiTranscribeAudio(audioB64: string) {
  const res = await fetch(`${API_BASE}/api/v1/voice/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ audio_b64: audioB64 }),
  });
  return res.json();
}

export async function apiRespond(conversationId: string | null, sessionId: string | null, content: string) {
  const res = await fetch(`${API_BASE}/api/v1/voice/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, session_id: sessionId, content }),
  });
  return res.json();
}

export async function apiSpeak(text: string) {
  const res = await fetch(`${API_BASE}/api/v1/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return res.json();
}

export async function apiVoiceWSUrl() {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? (typeof window !== 'undefined' ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}` : 'ws://127.0.0.1:8000');
  return `${base}/api/v1/voice/ws`;
}

export default { apiStartConversation, apiTranscribeAudio, apiRespond, apiSpeak, apiVoiceWSUrl };
