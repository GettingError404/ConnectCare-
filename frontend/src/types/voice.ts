export type VoiceConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export type VoiceClientEventType =
  | 'user_audio_chunk'
  | 'user_message'
  | 'start_conversation'
  | 'stop_conversation'
  | 'ping';

export type VoiceServerEventType =
  | 'transcription'
  | 'agent_thinking'
  | 'agent_response'
  | 'tts_audio_chunk'
  | 'conversation_started'
  | 'conversation_stopped'
  | 'error'
  | 'pong';

export interface VoiceServerEvent<Payload = any> {
  type: VoiceServerEventType;
  conversation_id: string | null;
  session_id: string | null;
  payload: Payload;
}

export interface VoiceClientEvent<Payload = any> {
  type: VoiceClientEventType;
  conversation_id: string | null;
  session_id: string | null;
  payload: Payload;
}

export interface VoiceEvent<Payload = any> extends VoiceServerEvent<Payload> {}

export interface VoiceTranscriptionPayload {
  text: string;
  confidence: number;
  source?: string;
}

export interface VoiceAgentResponsePayload {
  content: string;
  is_final: boolean;
}

export interface VoiceTTSPayload {
  audio_b64: string;
  is_last?: boolean;
}

export interface VoiceConversationStartedPayload {
  conversation_id: string;
  session_id: string;
}

export interface VoiceErrorPayload {
  message: string;
  code?: string;
}
