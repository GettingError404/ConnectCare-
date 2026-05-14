'use client';
import React, { useState } from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { Phone, Video, PhoneOff, Clock, User } from 'lucide-react';
import { Button } from '@/components/ui/button';

const CaregiverTelehealthPage: React.FC = () => {
  const { assignedElders } = useCaregiverStore();
  const [activeCall, setActiveCall] = useState<string | null>(null);
  const [callType, setCallType] = useState<'audio' | 'video'>('audio');

  const startCall = (elderId: string, type: 'audio' | 'video') => {
    setActiveCall(elderId);
    setCallType(type);
  };

  const endCall = () => setActiveCall(null);

  const callingElder = assignedElders.find(e => e.elderId === activeCall);

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Telehealth & Emergency Contact</h2>
        <p className="text-sm text-muted-foreground">Quick access to virtual consultations</p>
      </div>

      {activeCall && callingElder && (
        <div className="bg-primary/5 border-2 border-primary/30 rounded-2xl p-8 text-center">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4 text-3xl">
            {callType === 'video' ? '📹' : '📞'}
          </div>
          <h3 className="font-heading text-xl font-bold text-foreground">{callingElder.name}</h3>
          <p className="text-sm text-muted-foreground mt-1">{callType === 'video' ? 'Video' : 'Audio'} Call in Progress</p>
          <div className="flex items-center justify-center gap-2 mt-2 text-xs text-primary">
            <Clock className="w-3 h-3" /> Connected
          </div>
          <Button onClick={endCall} variant="destructive" className="mt-6">
            <PhoneOff className="w-4 h-4 mr-2" /> End Call
          </Button>
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Patients</h3>
        {assignedElders.map(e => (
          <div key={e.elderId} className="bg-card rounded-xl border border-border p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                <User className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-medium text-foreground text-sm">{e.name}</p>
                <div className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${e.status === 'online' ? 'bg-success' : 'bg-muted-foreground'}`} />
                  <span className="text-[10px] text-muted-foreground">{e.status}</span>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => startCall(e.elderId, 'audio')} disabled={activeCall !== null}>
                <Phone className="w-4 h-4" />
              </Button>
              <Button size="sm" variant="outline" onClick={() => startCall(e.elderId, 'video')} disabled={activeCall !== null}>
                <Video className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-destructive/5 border border-destructive/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-destructive mb-2">🚨 Emergency Contacts</h3>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between"><span className="text-foreground">Emergency Services</span><span className="text-muted-foreground font-mono">911</span></div>
          <div className="flex justify-between"><span className="text-foreground">Poison Control</span><span className="text-muted-foreground font-mono">1-800-222-1222</span></div>
          <div className="flex justify-between"><span className="text-foreground">Hospital (Main)</span><span className="text-muted-foreground font-mono">555-0100</span></div>
        </div>
      </div>
    </div>
  );
};

export default CaregiverTelehealthPage;


