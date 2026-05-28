'use client';

import ElderHeader from '@/components/elder/ElderHeader';
import VoiceCompanion from '@/components/elder/VoiceCompanion';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { useVoiceEngine } from '@/hooks/useVoiceEngine';

export default function ElderVoicePage() {
  const {
    voiceState,
    continuousMode,
    isListening,
    isSpeaking,
    transcript,
    speechError,
    sttSupported,
    connectionStatus,
    liveResponse,
    assistantDraft,
    toggleContinuous,
    processTextInput,
    cancelSpeech,
  } = useVoiceEngine();

  return (
    <AuthGuard allowedRoles={['elder']}>
      <div className="min-h-screen bg-elder-bg">
        <ElderHeader />
        <main className="mx-auto max-w-3xl px-4 py-6">
          <VoiceCompanion
            voiceState={voiceState}
            continuousMode={continuousMode}
            isListening={isListening}
            isSpeaking={isSpeaking}
            transcript={transcript}
            speechError={speechError}
            sttSupported={sttSupported}
            connectionStatus={connectionStatus}
            liveResponse={liveResponse}
            assistantDraft={assistantDraft}
            onToggleContinuous={toggleContinuous}
            onProcessText={processTextInput}
            onCancelSpeech={cancelSpeech}
          />
        </main>
      </div>
    </AuthGuard>
  );
}
