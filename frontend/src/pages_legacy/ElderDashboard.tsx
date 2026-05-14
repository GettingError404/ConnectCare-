'use client';
import React, { useState, useEffect, useCallback } from 'react';
import ElderHeader from '@/components/elder/ElderHeader';
import VoiceOrb from '@/components/elder/VoiceOrb';
import LiveTranscript from '@/components/elder/LiveTranscript';
import EntertainmentPanel from '@/components/elder/EntertainmentPanel';
import QuickActions from '@/components/elder/QuickActions';
import GamePanel from '@/components/elder/GamePanel';
import MusicPlayer from '@/components/elder/MusicPlayer';
import RemindersPanel from '@/components/elder/RemindersPanel';
import VitalsPanel from '@/components/elder/VitalsPanel';
import SmartHomePanel from '@/components/elder/SmartHomePanel';
import SOSPanel from '@/components/elder/SOSPanel';
import GamesHub from '@/components/elder/games/GamesHub';
import { useVoiceEngine } from '@/hooks/useVoiceEngine';
import { useBackgroundMonitor } from '@/hooks/useBackgroundMonitor';
import { useElderStore } from '@/store/elderStore';
import { MessageCircle, Pill, Heart, Home, Send, Gamepad2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

type Tab = 'companion' | 'reminders' | 'vitals' | 'home' | 'games';

const ElderDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('companion');
  const [textInput, setTextInput] = useState('');
  const { loadDashboardData, updateVitals, emergency, gameSession, musicPlayer } = useElderStore();

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  const handleNavigate = useCallback((tab: string) => {
    if (['companion', 'reminders', 'vitals', 'home', 'games'].includes(tab)) {
      setActiveTab(tab as Tab);
    }
  }, []);

  const voiceEngine = useVoiceEngine({
    onNavigate: handleNavigate,
    autoStart: false,
  });

  useBackgroundMonitor({
    enabled: voiceEngine.continuousMode,
    onProactiveSpeak: voiceEngine.speakProactive,
  });

  useEffect(() => {
    const interval = setInterval(updateVitals, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSendText = () => {
    if (!textInput.trim()) return;
    voiceEngine.processTextInput(textInput.trim());
    setTextInput('');
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'companion', label: 'Assistant', icon: <MessageCircle className="w-5 h-5" /> },
    { id: 'games', label: 'Games', icon: <Gamepad2 className="w-5 h-5" /> },
    { id: 'reminders', label: 'Reminders', icon: <Pill className="w-5 h-5" /> },
    { id: 'vitals', label: 'Health', icon: <Heart className="w-5 h-5" /> },
    { id: 'home', label: 'Home', icon: <Home className="w-5 h-5" /> },
  ];

  const isGameActive = gameSession.status === 'active' || gameSession.status === 'completed';
  const isMusicPlaying = musicPlayer.currentTrack !== null;

  // Speak function for games hub
  const handleGameSpeak = useCallback((text: string) => {
    voiceEngine.speakProactive(text, true);
  }, [voiceEngine]);

  return (
    <div className="min-h-screen bg-elder-bg flex flex-col">
      <ElderHeader />

      {/* Emergency banner */}
      {emergency.active && (
        <div className="px-4 pt-3 max-w-2xl mx-auto w-full">
          <SOSPanel />
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-0 pb-20 w-full max-w-2xl mx-auto">
        {activeTab === 'companion' && (
          <div className="flex-1 flex flex-col items-center justify-between px-4 pt-6">
            {/* Live transcript area */}
            <div className="w-full flex-1 min-h-0 overflow-y-auto mb-4">
              <LiveTranscript
                liveTranscript={voiceEngine.transcript}
                isListening={voiceEngine.isListening}
                maxMessages={5}
              />
            </div>

            {/* Music Player (persistent when playing) */}
            {isMusicPlaying && (
              <div className="w-full py-2">
                <MusicPlayer onVoiceCommand={voiceEngine.processTextInput} />
              </div>
            )}

            {/* Game Panel (when active) */}
            {isGameActive && (
              <div className="w-full py-2">
                <GamePanel onVoiceCommand={voiceEngine.processTextInput} />
              </div>
            )}

            {/* Central Voice Orb */}
            <div className="flex-shrink-0 py-4">
              <VoiceOrb
                state={voiceEngine.voiceState}
                onClick={voiceEngine.toggleContinuous}
                disabled={!voiceEngine.sttSupported}
              />
            </div>

            {/* Quick actions + entertainment (hide when game active) */}
            {!isGameActive && (
              <div className="w-full space-y-4 py-4">
                <QuickActions onVoiceCommand={voiceEngine.processTextInput} />

                {/* Expandable entertainment */}
                <details className="group max-w-md mx-auto">
                  <summary className="text-center text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors list-none">
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-card border border-border hover:border-primary/40 transition-colors">
                      Entertainment
                      <span className="group-open:rotate-180 transition-transform text-xs">▾</span>
                    </span>
                  </summary>
                  <div className="pt-3">
                    <EntertainmentPanel onVoiceCommand={voiceEngine.processTextInput} />
                  </div>
                </details>
              </div>
            )}

            {/* Text input fallback */}
            <div className="w-full max-w-md mx-auto flex gap-2 pb-2">
              <Input
                placeholder={isGameActive ? "Type your answer..." : "Or type a message..."}
                value={textInput}
                onChange={e => setTextInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSendText()}
                className="elder-text-base"
              />
              <Button onClick={handleSendText} size="icon" className="shrink-0">
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </div>
        )}

        {activeTab === 'games' && (
          <div className="flex-1 overflow-y-auto px-4 pt-3">
            <GamesHub onSpeak={handleGameSpeak} onBack={() => setActiveTab('companion')} />
          </div>
        )}

        {activeTab === 'reminders' && (
          <div className="flex-1 overflow-y-auto px-4 pt-3">
            <RemindersPanel />
          </div>
        )}
        {activeTab === 'vitals' && (
          <div className="flex-1 overflow-y-auto px-4 pt-3">
            <VitalsPanel />
          </div>
        )}
        {activeTab === 'home' && (
          <div className="flex-1 overflow-y-auto px-4 pt-3">
            <SmartHomePanel />
          </div>
        )}

        {/* Persistent voice indicator on non-companion tabs */}
        {activeTab !== 'companion' && voiceEngine.continuousMode && (
          <div className="fixed top-16 left-0 right-0 z-50 px-4 pt-2">
            <div className="bg-card/95 backdrop-blur-sm rounded-xl border border-border p-2.5 flex items-center justify-between shadow-md max-w-2xl mx-auto">
              <div className="flex items-center gap-2 min-w-0">
                <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                  voiceEngine.voiceState === 'listening' ? 'bg-primary animate-pulse' :
                  voiceEngine.voiceState === 'speaking' ? 'bg-success animate-pulse' :
                  voiceEngine.voiceState === 'processing' ? 'bg-info animate-pulse' :
                  'bg-muted-foreground'
                }`} />
                <span className="text-xs font-semibold text-foreground">
                  {voiceEngine.voiceState === 'listening' ? 'Listening' :
                   voiceEngine.voiceState === 'speaking' ? 'Speaking' :
                   voiceEngine.voiceState === 'processing' ? 'Thinking' :
                   'Voice active'}
                </span>
                {voiceEngine.transcript && voiceEngine.isListening && (
                  <span className="text-xs text-muted-foreground italic truncate">"{voiceEngine.transcript}"</span>
                )}
              </div>
              <button
                onClick={voiceEngine.toggleContinuous}
                className="text-xs text-destructive font-semibold px-2.5 py-1 rounded-lg hover:bg-destructive/10 transition-colors shrink-0"
              >
                Stop
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-0 right-0 bg-card/95 backdrop-blur border-t border-border px-2 py-2 flex justify-around z-50">
        <div className="flex justify-around w-full max-w-2xl mx-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center gap-1 py-1 px-2 rounded-xl transition-colors focus-ring min-w-[56px] ${
                activeTab === tab.id
                  ? 'text-primary bg-primary/10'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.icon}
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
};

export default ElderDashboard;


