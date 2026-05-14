'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  Users, MessageCircle, X, Volume2, Video, Phone, Send, ArrowLeft,
  Calendar, Sparkles, Hand, Music2, BookOpen, Brain, Coffee, Heart,
} from 'lucide-react';

interface ClubRoom {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  participants: number;
  description: string;
  status: 'open' | 'live' | 'starting_soon';
  schedule?: string;
}

interface Member {
  id: string;
  name: string;
  initials: string;
  status: 'online' | 'away' | 'in_call';
  city: string;
  age: number;
}

interface GroupEvent {
  id: string;
  title: string;
  time: string;
  host: string;
  attendees: number;
  icon: React.ComponentType<{ className?: string }>;
}

const ROOMS: ClubRoom[] = [
  { id: 'r1', name: 'Morning Quiz',  icon: Brain,    participants: 5, description: 'A friendly daily quiz with fellow members', status: 'open' },
  { id: 'r2', name: 'Story Circle',  icon: BookOpen, participants: 3, description: 'Share memories and listen to stories',     status: 'open' },
  { id: 'r3', name: 'Music Lounge',  icon: Music2,   participants: 7, description: 'Listen to classic songs together',         status: 'live' },
  { id: 'r4', name: 'Tea & Chat',    icon: Coffee,   participants: 2, description: 'Open chat room — drop in any time',        status: 'open',  schedule: '10:30 AM' },
];

const MEMBERS: Member[] = [
  { id: 'm1', name: 'Sunita Sharma', initials: 'SS', status: 'online',  city: 'Pune',      age: 68 },
  { id: 'm2', name: 'Ramesh Kumar',  initials: 'RK', status: 'online',  city: 'Mumbai',    age: 72 },
  { id: 'm3', name: 'Anita Patel',   initials: 'AP', status: 'in_call', city: 'Ahmedabad', age: 70 },
  { id: 'm4', name: 'Vinod Rao',     initials: 'VR', status: 'away',    city: 'Bengaluru', age: 75 },
  { id: 'm5', name: 'Lakshmi Iyer',  initials: 'LI', status: 'online',  city: 'Chennai',   age: 67 },
];

const EVENTS: GroupEvent[] = [
  { id: 'e1', title: 'Yoga & Breathing', time: 'Today · 5:00 PM',    host: 'Dr. Mehra',   attendees: 12, icon: Heart  },
  { id: 'e2', title: 'Bhajan Sandhya',   time: 'Tomorrow · 6:30 PM', host: 'Music Group', attendees: 24, icon: Music2 },
  { id: 'e3', title: 'Memory Workshop',  time: 'Sat · 11:00 AM',     host: 'Care Team',   attendees: 8,  icon: Brain  },
];

interface SeniorClubProps {
  onExit: () => void;
  onSpeak: (text: string) => void;
}

type View = 'home' | 'room' | 'call';

const statusDot: Record<Member['status'], string> = {
  online: 'bg-success',
  away: 'bg-warning',
  in_call: 'bg-info',
};

const statusLabel: Record<Member['status'], string> = {
  online: 'Online',
  away: 'Away',
  in_call: 'In a call',
};

const SeniorClub: React.FC<SeniorClubProps> = ({ onExit, onSpeak }) => {
  const [view, setView] = useState<View>('home');
  const [room, setRoom] = useState<ClubRoom | null>(null);
  const [callMember, setCallMember] = useState<Member | null>(null);
  const [callMode, setCallMode] = useState<'voice' | 'video'>('voice');
  const [callSeconds, setCallSeconds] = useState(0);
  const [messages, setMessages] = useState<{ from: string; text: string; you?: boolean; system?: boolean; ts?: string }[]>([]);
  const [draft, setDraft] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    onSpeak('Welcome to the Senior Club. Join a room, see members, or attend an event.');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Call timer
  useEffect(() => {
    if (view !== 'call') return;
    const t = setInterval(() => setCallSeconds(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [view]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const joinRoom = (r: ClubRoom) => {
    setRoom(r);
    setView('room');
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages([
      { from: 'System', text: `You joined ${r.name} · ${now}`, system: true },
      { from: 'Sunita Sharma', text: `Welcome to ${r.name}! 😊 So glad you're here.` },
      { from: 'Ramesh Kumar', text: 'Hello friend! How has your day been?' },
    ]);
    onSpeak(`You joined ${r.name}. Say hello to everyone!`);
  };

  const leaveRoom = () => {
    setRoom(null);
    setMessages([]);
    setView('home');
    onSpeak('You left the room.');
  };

  const generateReply = (userText: string): { from: string; text: string } => {
    const t = userText.toLowerCase();
    const speakers = ['Anita Patel', 'Vinod Rao', 'Lakshmi Iyer', 'Sunita Sharma', 'Ramesh Kumar'];
    const who = speakers[Math.floor(Math.random() * speakers.length)];
    let text = '';
    if (/^(hi|hello|hey|namaste|namaskar|good\s*(morning|afternoon|evening))/.test(t)) {
      text = ['Hello dear, lovely to see you! 🌼', 'Namaste 🙏 How are you today?', 'Hi there! Welcome back.'][Math.floor(Math.random() * 3)];
    } else if (/how\s*are\s*you|kaise/.test(t)) {
      text = ['I am doing well, thank you for asking! How about you?', 'Blessed and grateful 🙏 You?'][Math.floor(Math.random() * 2)];
    } else if (/\?$/.test(userText.trim())) {
      text = ['That is a thoughtful question. Let me think…', 'Good question! What do others feel?', 'Hmm, I would say it depends on the day.'][Math.floor(Math.random() * 3)];
    } else if (/sad|lonely|tired|pain|miss/.test(t)) {
      text = ['Sending you warm hugs ❤️ We are here for you.', 'Take a deep breath, dear. You are not alone.', 'I understand. Please rest well today.'][Math.floor(Math.random() * 3)];
    } else if (/happy|good|great|wonderful|nice|grateful/.test(t)) {
      text = ['That makes me smile! 😊', 'How wonderful — keep that joy going!', 'God bless you 🙏'][Math.floor(Math.random() * 3)];
    } else if (/music|song|bhajan/.test(t)) {
      text = ['I love the old melodies the most.', 'Music heals the heart, doesn\'t it?'][Math.floor(Math.random() * 2)];
    } else if (/family|son|daughter|grand/.test(t)) {
      text = ['Family is everything ❤️', 'How lovely — give them my regards!'][Math.floor(Math.random() * 2)];
    } else {
      text = ['That is wonderful to hear.', 'I agree with you, dear.', 'Tell us a little more!', 'Bless you 🙏', 'How nice — thank you for sharing.'][Math.floor(Math.random() * 5)];
    }
    return { from: who, text };
  };

  const sendMessage = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages(prev => [...prev, { from: 'You', text: trimmed, you: true }]);
    setDraft('');
    // Typing indicator + content-aware reply
    const delay = 700 + Math.min(1800, trimmed.length * 25);
    setTimeout(() => {
      const reply = generateReply(trimmed);
      setMessages(prev => [...prev, reply]);
    }, delay);
    // Sometimes a second person chimes in
    if (Math.random() > 0.55) {
      setTimeout(() => {
        const reply2 = generateReply(trimmed);
        setMessages(prev => [...prev, reply2]);
      }, delay + 1500);
    }
  };

  const sayHello = () => {
    sendMessage('Hello everyone! 👋');
    onSpeak('You said hello to the group.');
  };

  const startCall = (m: Member, mode: 'voice' | 'video') => {
    setCallMember(m);
    setCallMode(mode);
    setCallSeconds(0);
    setView('call');
    onSpeak(`Connecting a ${mode} call with ${m.name}.`);
  };

  const endCall = () => {
    onSpeak(`Call with ${callMember?.name} ended.`);
    setCallMember(null);
    setView('home');
  };

  // Voice command bridge
  useEffect(() => {
    type WindowWithSeniorClubCommand = Window & {
      __seniorClubCommand?: (command: string) => void;
    };

    (window as WindowWithSeniorClubCommand).__seniorClubCommand = (command: string) => {
      const lower = command.toLowerCase();
      if (/exit|quit|back|leave/.test(lower)) {
        if (view === 'call') endCall();
        else if (view === 'room') leaveRoom();
        else onExit();
      } else if (/hello|hi|hey/.test(lower) && view === 'room') {
        sayHello();
      } else if (/join/.test(lower)) {
        const r = ROOMS.find(x => lower.includes(x.name.toLowerCase())) || ROOMS.find(x => x.status === 'open');
        if (r) joinRoom(r);
      } else if (/repeat|help/.test(lower)) {
        onSpeak(view === 'room'
          ? `You are in ${room?.name}. Say hello, or say leave to exit.`
          : 'Say join to enter a room, or pick one by name.');
      }
    };

    return () => {
      delete (window as WindowWithSeniorClubCommand).__seniorClubCommand;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, room]);


  // ===== CALL VIEW =====
  if (view === 'call' && callMember) {
    const mins = String(Math.floor(callSeconds / 60)).padStart(2, '0');
    const secs = String(callSeconds % 60).padStart(2, '0');
    return (
      <div className="flex flex-col items-center justify-between min-h-[calc(100vh-180px)] p-4 animate-fade-in">
        <div className="w-full flex items-center justify-between max-w-md">
          <Button variant="ghost" size="icon" onClick={endCall} aria-label="Back">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <span className="text-sm font-medium text-muted-foreground">{callMode === 'video' ? 'Video Call' : 'Voice Call'}</span>
          <div className="w-10" />
        </div>

        <div className="flex flex-col items-center gap-4 mt-8">
          <div className={`w-32 h-32 rounded-full flex items-center justify-center text-3xl font-bold text-primary-foreground bg-gradient-to-br from-primary to-primary/70 shadow-xl ring-4 ring-primary/20 ${callMode === 'video' ? '' : 'animate-pulse'}`}>
            {callMember.initials}
          </div>
          <div className="text-center">
            <p className="text-xl font-semibold text-foreground">{callMember.name}</p>
            <p className="text-sm text-muted-foreground mt-0.5">{callMember.city} · age {callMember.age}</p>
            <p className="text-base font-mono text-primary mt-3">{mins}:{secs}</p>
          </div>
        </div>

        <div className="flex gap-4 mt-8 mb-4">
          <button
            onClick={() => onSpeak('Microphone toggled.')}
            className="w-14 h-14 rounded-full bg-muted hover:bg-muted/70 flex items-center justify-center transition focus-ring"
            aria-label="Mute"
          >
            <Volume2 className="w-6 h-6 text-foreground" />
          </button>
          <button
            onClick={endCall}
            className="w-16 h-16 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90 flex items-center justify-center transition shadow-lg focus-ring"
            aria-label="End call"
          >
            <Phone className="w-7 h-7 rotate-[135deg]" />
          </button>
          <button
            onClick={() => setCallMode(m => m === 'voice' ? 'video' : 'voice')}
            className="w-14 h-14 rounded-full bg-muted hover:bg-muted/70 flex items-center justify-center transition focus-ring"
            aria-label="Toggle video"
          >
            <Video className="w-6 h-6 text-foreground" />
          </button>
        </div>
      </div>
    );
  }

  // ===== ROOM VIEW =====
  if (view === 'room' && room) {
    const RoomIcon = room.icon;
    const onlineMembers = MEMBERS.filter(m => m.status !== 'away');
    return (
      <div className="flex flex-col gap-3 max-w-3xl mx-auto p-2 animate-fade-in h-[calc(100vh-180px)] min-h-[560px]">
        {/* Header */}
        <div className="flex items-center justify-between rounded-2xl bg-card border border-border px-3 py-2.5">
          <Button variant="ghost" size="icon" onClick={leaveRoom} aria-label="Back">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3 flex-1 justify-center">
            <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center ring-1 ring-primary/15">
              <RoomIcon className="w-5 h-5" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-foreground leading-tight text-base">{room.name}</p>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                <span className="inline-flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                  {room.participants + 1} active
                </span>
                <span>·</span>
                <span>{room.description}</span>
              </p>
            </div>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" onClick={() => onSpeak(`You are in ${room.name}. Type or say a message.`)} aria-label="Repeat">
              <Volume2 className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => startCall(MEMBERS[0], 'voice')} aria-label="Voice call">
              <Phone className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Main: chat + member sidebar */}
        <div className="flex gap-3 flex-1 min-h-0">
          {/* Chat column */}
          <div className="flex flex-col flex-1 min-w-0 rounded-2xl bg-card border border-border overflow-hidden">
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.you ? 'justify-end' : m.system ? 'justify-center' : 'justify-start'}`}>
                  {m.system ? (
                    <p className="text-[11px] text-muted-foreground italic px-3 py-1 rounded-full bg-muted/50">{m.text}</p>
                  ) : (
                    <div className={`flex gap-2 max-w-[82%] ${m.you ? 'flex-row-reverse' : 'flex-row'}`}>
                      {!m.you && (
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/80 to-primary text-primary-foreground flex items-center justify-center text-[11px] font-semibold shrink-0">
                          {m.from.split(' ').map(p => p[0]).slice(0, 2).join('')}
                        </div>
                      )}
                      <div className={`px-4 py-2.5 rounded-2xl ${
                        m.you
                          ? 'bg-primary text-primary-foreground rounded-br-md'
                          : 'bg-muted text-foreground rounded-bl-md'
                      }`}>
                        {!m.you && <p className="text-[11px] font-semibold opacity-75 mb-0.5">{m.from}</p>}
                        <p className="leading-relaxed text-[15px]">{m.text}</p>
                        {m.ts && <p className="text-[10px] opacity-60 mt-1 text-right">{m.ts}</p>}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Composer */}
            <div className="border-t border-border p-3 bg-card">
              <div className="flex gap-2">
                <input
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(draft); } }}
                  placeholder="Type a message and press Enter…"
                  className="flex-1 px-4 py-3 rounded-xl border border-border bg-background text-[15px] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition"
                  aria-label="Message"
                />
                <Button onClick={() => sendMessage(draft)} size="lg" className="rounded-xl px-5" disabled={!draft.trim()} aria-label="Send">
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex gap-2 mt-2">
                <Button onClick={sayHello} variant="outline" size="sm" className="gap-1.5 h-8 text-xs">
                  <Hand className="w-3.5 h-3.5" /> Hello
                </Button>
                <Button onClick={() => sendMessage('How is everyone today? 🌼')} variant="outline" size="sm" className="h-8 text-xs">
                  How are you?
                </Button>
                <Button onClick={() => sendMessage('Thank you, friends 🙏')} variant="outline" size="sm" className="h-8 text-xs">
                  Thank you
                </Button>
                <Button onClick={leaveRoom} variant="ghost" size="sm" className="ml-auto h-8 text-xs text-destructive hover:text-destructive">
                  Leave
                </Button>
              </div>
            </div>
          </div>

          {/* Member sidebar */}
          <div className="hidden md:flex flex-col w-52 rounded-2xl bg-card border border-border p-3 overflow-y-auto">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">In this room</p>
            <div className="space-y-2">
              {onlineMembers.map(m => (
                <div key={m.id} className="flex items-center gap-2.5">
                  <div className="relative shrink-0">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/80 to-primary text-primary-foreground flex items-center justify-center text-xs font-semibold">
                      {m.initials}
                    </div>
                    <span className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full ring-2 ring-card ${statusDot[m.status]}`} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{m.name.split(' ')[0]}</p>
                    <p className="text-[10px] text-muted-foreground">{statusLabel[m.status]}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 max-w-2xl mx-auto p-2 animate-fade-in">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="icon" onClick={onExit} aria-label="Back">
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="text-center">
          <h2 className="font-heading text-xl font-semibold text-foreground tracking-tight">Senior Club</h2>
          <p className="text-xs text-muted-foreground mt-0.5">A community for friendly companionship</p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => onSpeak('Pick a room to join, view members, or attend an event.')} aria-label="Repeat">
          <Volume2 className="w-5 h-5" />
        </Button>
      </div>

      {/* Hero stat strip */}
      <div className="grid grid-cols-3 gap-2">
        <div className="card-elevated rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-primary">{MEMBERS.filter(m => m.status === 'online').length}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-medium">Online now</p>
        </div>
        <div className="card-elevated rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-info">{ROOMS.length}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-medium">Active rooms</p>
        </div>
        <div className="card-elevated rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-warning">{EVENTS.length}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-medium">Events</p>
        </div>
      </div>

      {/* Active rooms */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-foreground">Active Rooms</h3>
          <span className="text-xs text-muted-foreground">{ROOMS.length} rooms</span>
        </div>
        <div className="space-y-2">
          {ROOMS.map(r => {
            const Icon = r.icon;
            return (
              <button
                key={r.id}
                onClick={() => joinRoom(r)}
                className="w-full flex items-center gap-3 p-3.5 rounded-xl bg-card border border-border hover:border-primary/40 hover:shadow-sm active:scale-[0.99] transition-all text-left focus-ring"
              >
                <div className="w-11 h-11 rounded-xl bg-primary/8 text-primary flex items-center justify-center ring-1 ring-primary/15 shrink-0">
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground text-sm">{r.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{r.description}</p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Users className="w-3 h-3" /> {r.participants}
                  </div>
                  <span className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ring-1 ${
                    r.status === 'live' ? 'bg-destructive/10 text-destructive ring-destructive/15' :
                    r.status === 'starting_soon' ? 'bg-warning/10 text-warning ring-warning/15' :
                    'bg-success/10 text-success ring-success/15'
                  }`}>
                    {r.status === 'live' ? 'Live' : r.status === 'starting_soon' ? 'Soon' : 'Open'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Members */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-foreground">Members</h3>
          <span className="text-xs text-muted-foreground">{MEMBERS.length} members</span>
        </div>
        <div className="space-y-2">
          {MEMBERS.map(m => (
            <div key={m.id} className="flex items-center gap-3 p-3 rounded-xl bg-card border border-border">
              <div className="relative shrink-0">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-primary/80 to-primary text-primary-foreground flex items-center justify-center text-sm font-semibold">
                  {m.initials}
                </div>
                <span className={`absolute bottom-0 right-0 w-3 h-3 rounded-full ring-2 ring-card ${statusDot[m.status]}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-foreground text-sm truncate">{m.name}</p>
                <p className="text-xs text-muted-foreground">{m.city} · {statusLabel[m.status]}</p>
              </div>
              <div className="flex gap-1.5 shrink-0">
                <button
                  onClick={() => startCall(m, 'voice')}
                  disabled={m.status === 'in_call'}
                  className="w-9 h-9 rounded-lg bg-success/10 text-success hover:bg-success/15 disabled:opacity-40 flex items-center justify-center transition focus-ring"
                  aria-label={`Voice call ${m.name}`}
                >
                  <Phone className="w-4 h-4" />
                </button>
                <button
                  onClick={() => startCall(m, 'video')}
                  disabled={m.status === 'in_call'}
                  className="w-9 h-9 rounded-lg bg-info/10 text-info hover:bg-info/15 disabled:opacity-40 flex items-center justify-center transition focus-ring"
                  aria-label={`Video call ${m.name}`}
                >
                  <Video className="w-4 h-4" />
                </button>
                <button
                  onClick={() => { setMessages([{ from: 'System', text: `Direct chat with ${m.name}`, system: true }]); setRoom({ id: 'dm', name: m.name, icon: MessageCircle, participants: 0, description: 'Direct chat', status: 'open' }); setView('room'); }}
                  className="w-9 h-9 rounded-lg bg-primary/10 text-primary hover:bg-primary/15 flex items-center justify-center transition focus-ring"
                  aria-label={`Message ${m.name}`}
                >
                  <MessageCircle className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Group events */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5"><Calendar className="w-4 h-4" /> Upcoming Events</h3>
          <span className="text-xs text-muted-foreground">{EVENTS.length} events</span>
        </div>
        <div className="space-y-2">
          {EVENTS.map(e => {
            const Icon = e.icon;
            return (
              <div key={e.id} className="flex items-center gap-3 p-3 rounded-xl bg-card border border-border">
                <div className="w-10 h-10 rounded-xl bg-warning/10 text-warning flex items-center justify-center ring-1 ring-warning/15 shrink-0">
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground text-sm">{e.title}</p>
                  <p className="text-xs text-muted-foreground">{e.time} · with {e.host}</p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => { onSpeak(`You are registered for ${e.title}.`); }}
                  className="shrink-0 gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Join
                </Button>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default SeniorClub;

