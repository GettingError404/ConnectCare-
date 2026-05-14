import { create } from 'zustand';
import { Reminder, VitalSign, MoodEntry, ChatMessage, SmartDevice, CheckInSession, EmergencyState, WellnessReward, FamilyContact, CallState, GameSession, MusicPlayerState, User } from '@/types';
import { quizQuestions, memoryPairs, wordPuzzles, musicLibrary } from '@/data/gameData';
import { profileService } from '@/lib/api/services/profile';
import { telemetryService, type TelemetryReading } from '@/lib/api/services/telemetry';
import { alertsService } from '@/lib/api/services/alerts';
import { devicesService } from '@/lib/api/services/devices';

interface ElderState {
  profile: User | null;
  reminders: Reminder[];
  vitals: VitalSign[];
  vitalsHistory: {
    heart_rate: { time: string; value: number }[];
    blood_pressure_sys: { day: string; value: number }[];
    glucose: { day: string; value: number }[];
    activity: { day: string; value: number }[];
  };
  moodHistory: MoodEntry[];
  chatMessages: ChatMessage[];
  smartDevices: SmartDevice[];
  checkIn: CheckInSession;
  emergency: EmergencyState;
  wellnessStars: number;
  streak: number;
  rewards: WellnessReward[];
  familyContacts: FamilyContact[];
  callState: CallState;
  gameSession: GameSession;
  musicPlayer: MusicPlayerState;
  isLoading: boolean;
  lastHydratedAt: string | null;
  
  loadDashboardData: () => Promise<void>;
  updateReminderStatus: (id: string, status: Reminder['status']) => void;
  addMoodEntry: (entry: MoodEntry) => void;
  addChatMessage: (msg: ChatMessage) => void;
  toggleDevice: (id: string) => void;
  updateCheckIn: (questionId: string, answer: string, score: number) => void;
  completeCheckIn: () => void;
  triggerEmergency: (by: EmergencyState['triggeredBy']) => void;
  resolveEmergency: () => void;
  addStars: (amount: number, action: string) => void;
  updateVitals: () => void;
  initiateCall: (contactId: string) => void;
  endCall: () => void;
  cancelCall: () => void;
  findContactByAlias: (alias: string) => FamilyContact | undefined;
  // Game actions
  startGame: (type: 'quiz' | 'memory' | 'word') => void;
  answerGame: (answer: string) => { correct: boolean; correctAnswer?: string; done: boolean };
  endGame: () => void;
  // Music actions
  playMusic: (genre?: string) => void;
  toggleMusicPlayback: () => void;
  nextTrack: () => void;
  prevTrack: () => void;
  stopMusic: () => void;
}

const defaultGameSession: GameSession = { type: 'quiz', status: 'idle', currentQuestion: 0, totalQuestions: 0, score: 0 };
const defaultMusicPlayer: MusicPlayerState = { status: 'idle', currentTrack: null, queue: [] };
const emptyCheckIn: CheckInSession = {
  id: 'checkin-live',
  date: new Date().toISOString().split('T')[0],
  status: 'pending',
  questions: [
    { id: 'q1', category: 'mood', question: 'How are you feeling right now?' },
    { id: 'q2', category: 'memory', question: 'What did you have to eat today?' },
    { id: 'q3', category: 'mobility', question: 'Have you moved around comfortably today?' },
    { id: 'q4', category: 'medication', question: 'Have you taken your medicines as scheduled?' },
  ],
};

const emptyVitalsHistory = {
  heart_rate: [] as { time: string; value: number }[],
  blood_pressure_sys: [] as { day: string; value: number }[],
  glucose: [] as { day: string; value: number }[],
  activity: [] as { day: string; value: number }[],
};

// Helper to shuffle array
function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function toVitalType(reading: TelemetryReading): VitalSign[] {
  const timestamp = reading.recorded_at;
  const vitals: VitalSign[] = [];

  if (typeof reading.heart_rate === 'number') {
    vitals.push({ id: `hr-${reading.id}`, type: 'heart_rate', value: reading.heart_rate, unit: 'bpm', timestamp, status: reading.heart_rate >= 100 ? 'warning' : 'normal', trend: 'stable' });
  }

  if (typeof reading.spo2 === 'number') {
    vitals.push({ id: `spo2-${reading.id}`, type: 'spo2', value: reading.spo2, unit: '%', timestamp, status: reading.spo2 < 95 ? 'warning' : 'normal', trend: 'stable' });
  }

  if (typeof reading.glucose_level === 'number') {
    vitals.push({ id: `glu-${reading.id}`, type: 'glucose', value: reading.glucose_level, unit: 'mg/dL', timestamp, status: reading.glucose_level > 140 ? 'warning' : 'normal', trend: 'stable' });
  }

  if (typeof reading.body_temperature === 'number') {
    vitals.push({ id: `temp-${reading.id}`, type: 'temperature', value: reading.body_temperature, unit: '°F', timestamp, status: reading.body_temperature > 99.5 ? 'warning' : 'normal', trend: 'stable' });
  }

  if (typeof reading.systolic_bp === 'number' && typeof reading.diastolic_bp === 'number') {
    vitals.push({ id: `bp-${reading.id}`, type: 'blood_pressure', value: `${reading.systolic_bp}/${reading.diastolic_bp}`, unit: 'mmHg', timestamp, status: reading.systolic_bp >= 130 || reading.diastolic_bp >= 80 ? 'warning' : 'normal', trend: 'stable' });
  }

  return vitals;
}

function buildVitalsHistory(readings: TelemetryReading[]) {
  const sorted = [...readings].sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime());
  const heart_rate = sorted
    .filter(r => typeof r.heart_rate === 'number')
    .slice(-24)
    .map(r => ({ time: new Date(r.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), value: Number(r.heart_rate) }));

  const blood_pressure_sys = sorted
    .filter(r => typeof r.systolic_bp === 'number')
    .slice(-7)
    .map(r => ({ day: new Date(r.recorded_at).toLocaleDateString([], { weekday: 'short' }), value: Number(r.systolic_bp) }));

  const glucose = sorted
    .filter(r => typeof r.glucose_level === 'number')
    .slice(-7)
    .map(r => ({ day: new Date(r.recorded_at).toLocaleDateString([], { weekday: 'short' }), value: Number(r.glucose_level) }));

  const activity = sorted
    .filter(r => typeof r.heart_rate === 'number')
    .slice(-7)
    .map(r => ({ day: new Date(r.recorded_at).toLocaleDateString([], { weekday: 'short' }), value: Math.max(0, Math.round((Number(r.heart_rate) - 50) * 120)) }));

  return { heart_rate, blood_pressure_sys, glucose, activity };
}

export const useElderStore = create<ElderState>((set, get) => ({
  profile: null,
  reminders: [],
  vitals: [],
  vitalsHistory: { ...emptyVitalsHistory },
  moodHistory: [],
  chatMessages: [],
  smartDevices: [],
  checkIn: { ...emptyCheckIn },
  emergency: { active: false, severity: 'low', updates: [] },
  wellnessStars: 0,
  streak: 0,
  rewards: [],
  familyContacts: [],
  callState: { status: 'idle' },
  gameSession: { ...defaultGameSession },
  musicPlayer: { ...defaultMusicPlayer },
  isLoading: false,
  lastHydratedAt: null,

  loadDashboardData: async () => {
    set({ isLoading: true });
    try {
      const profileResponse = await profileService.getCurrentUser();
      if (!profileResponse.ok) {
        set({ isLoading: false });
        return;
      }

      const profile = profileResponse.data;
      const telemetryResponse = await telemetryService.getTelemetryTimeline(profile.id, 100);
      const latestResponse = await telemetryService.getLatestTelemetry(profile.id, 24);
      const devicesResponse = await devicesService.getMyDevices();
      const alertsResponse = await alertsService.getMyAlerts();

      const timeline = telemetryResponse.ok ? telemetryResponse.data : [];
      const latest = latestResponse.ok ? latestResponse.data : [];
      const devices = devicesResponse.ok ? devicesResponse.data : [];
      const alerts = alertsResponse.ok ? alertsResponse.data : [];

      const vitals = latest.flatMap(toVitalType);
      const history = buildVitalsHistory(timeline);

      set({
        profile: {
          id: profile.id,
          email: profile.email,
          name: profile.name,
          role: (profile.role ?? profile.roles?.[0] ?? 'elder') as User['role'],
          createdAt: profile.created_at,
        },
        vitals,
        vitalsHistory: history,
        smartDevices: devices.map(device => ({
          id: device.id,
          name: device.name,
          type: 'thermostat',
          status: 'on',
          room: 'Home',
          lastUpdated: device.created_at,
        })),
        reminders: [],
        moodHistory: [],
        chatMessages: [],
        familyContacts: [],
        rewards: [],
        wellnessStars: alerts.filter(alert => !alert.is_resolved).length,
        streak: history.heart_rate.length,
        lastHydratedAt: new Date().toISOString(),
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  updateReminderStatus: (id, status) =>
    set(s => ({
      reminders: s.reminders.map(r => r.id === id ? { ...r, status } : r),
    })),

  addMoodEntry: (entry) =>
    set(s => ({ moodHistory: [entry, ...s.moodHistory] })),

  addChatMessage: (msg) =>
    set(s => ({ chatMessages: [...s.chatMessages, msg] })),

  toggleDevice: (id) =>
    set(s => ({
      smartDevices: s.smartDevices.map(d => {
        if (d.id !== id) return d;
        const newStatus = d.type === 'light' ? (d.status === 'on' ? 'off' : 'on')
          : d.type === 'lock' ? (d.status === 'locked' ? 'unlocked' : 'locked')
          : d.type === 'door' ? (d.status === 'open' ? 'closed' : 'open')
          : d.status;
        return { ...d, status: newStatus, lastUpdated: new Date().toISOString() };
      }),
    })),

  updateCheckIn: (questionId, answer, score) =>
    set(s => ({
      checkIn: {
        ...s.checkIn,
        status: 'in_progress',
        questions: s.checkIn.questions.map(q =>
          q.id === questionId ? { ...q, answer, score } : q
        ),
      },
    })),

  completeCheckIn: () =>
    set(s => {
      const answered = s.checkIn.questions.filter(q => q.score !== undefined);
      const avg = answered.length ? answered.reduce((a, q) => a + (q.score || 0), 0) / answered.length : 0;
      return {
        checkIn: { ...s.checkIn, status: 'completed', overallScore: Math.round(avg * 10) / 10, summary: `Completed with score ${avg.toFixed(1)}/10` },
      };
    }),

  triggerEmergency: (by) =>
    set(() => ({
      emergency: {
        active: true, severity: 'critical', triggeredAt: new Date().toISOString(), triggeredBy: by, status: 'triggered',
        updates: [
          { message: 'Emergency triggered', timestamp: new Date().toISOString() },
          { message: 'Notifying family members...', timestamp: new Date(Date.now() + 2000).toISOString() },
          { message: 'Family notified successfully', timestamp: new Date(Date.now() + 5000).toISOString() },
        ],
      },
    })),

  resolveEmergency: () =>
    set(() => ({ emergency: { active: false, severity: 'low', updates: [] } })),

  addStars: (amount, action) =>
    set(s => ({
      wellnessStars: s.wellnessStars + amount,
      rewards: [...s.rewards, { id: `wr-${Date.now()}`, action, stars: amount, timestamp: new Date().toISOString() }],
    })),

  updateVitals: () =>
    get().loadDashboardData(),

  initiateCall: (contactId) =>
    set(s => {
      const contact = s.familyContacts.find(c => c.id === contactId);
      if (!contact) return {};
      setTimeout(() => {
        const current = get().callState;
        if (current.status === 'calling' && current.contactId === contactId) {
          set({ callState: { status: 'connected', contactId, contactName: contact.name, startedAt: new Date().toISOString() } });
        }
      }, 2000);
      return { callState: { status: 'calling', contactId, contactName: contact.name, startedAt: new Date().toISOString() } };
    }),

  endCall: () => set(() => ({ callState: { status: 'ended' } })),
  cancelCall: () => set(() => ({ callState: { status: 'cancelled' } })),

  findContactByAlias: (alias) => {
    const lower = alias.toLowerCase();
    return get().familyContacts.find(c =>
      c.aliases.some(a => lower.includes(a)) ||
      c.name.toLowerCase().includes(lower) ||
      c.relationship.toLowerCase().includes(lower)
    );
  },

  // === GAME ACTIONS ===
  startGame: (type) => {
    if (type === 'quiz') {
      const questions = shuffle(quizQuestions).slice(0, 5);
      const q = questions[0];
      set({
        gameSession: {
          type: 'quiz', status: 'active', currentQuestion: 0, totalQuestions: 5, score: 0,
          quizData: { question: q.question, options: q.options, correctIndex: q.correctIndex },
        },
      });
      // Store questions in closure via a simple approach - we'll use the store itself
      (get() as { _quizQuestions?: typeof questions })._quizQuestions = questions;

    } else if (type === 'memory') {
      const cards = shuffle(memoryPairs).slice(0, 3);
      set({
        gameSession: {
          type: 'memory', status: 'active', currentQuestion: 0, totalQuestions: 4, score: 0,
          memoryData: { sequence: cards, revealed: true },
        },
      });
      // Hide after 3 seconds
      setTimeout(() => {
        const gs = get().gameSession;
        if (gs.type === 'memory' && gs.memoryData?.revealed) {
          set({ gameSession: { ...gs, memoryData: { ...gs.memoryData!, revealed: false } } });
        }
      }, 4000);
      (get() as { _memoryRound?: number })._memoryRound = 0;

    } else if (type === 'word') {
      const puzzles = shuffle(wordPuzzles).slice(0, 5);
      const p = puzzles[0];
      set({
        gameSession: {
          type: 'word', status: 'active', currentQuestion: 0, totalQuestions: 5, score: 0,
          wordData: { scrambled: p.scrambled, answer: p.answer, hint: p.hint },
        },
      });
      (get() as { _wordPuzzles?: typeof puzzles })._wordPuzzles = puzzles;

    }
  },

  answerGame: (answer) => {
    const gs = get().gameSession;
    if (gs.status !== 'active') return { correct: false, done: true };
    const lower = answer.toLowerCase().trim();
    let correct = false;
    let correctAnswer: string | undefined;
    
    if (gs.type === 'quiz' && gs.quizData) {
      const correctOpt = gs.quizData.options[gs.quizData.correctIndex];
      correctAnswer = correctOpt;
      correct = lower.includes(correctOpt.toLowerCase()) || 
                lower === ['a', 'b', 'c', 'd'][gs.quizData.correctIndex] ||
                lower === String(gs.quizData.correctIndex + 1);
    } else if (gs.type === 'word' && gs.wordData) {
      correctAnswer = gs.wordData.answer;
      correct = lower === gs.wordData.answer.toLowerCase();
    } else if (gs.type === 'memory' && gs.memoryData) {
      const expected = gs.memoryData.sequence.map(s => s.label.toLowerCase());
      const words = lower.split(/[\s,]+/).filter(Boolean);
      correct = expected.every((e, i) => words[i] && words[i].includes(e));
      correctAnswer = gs.memoryData.sequence.map(s => `${s.emoji} ${s.label}`).join(', ');
    }

    const newScore = gs.score + (correct ? 1 : 0);
    const nextQ = gs.currentQuestion + 1;
    const done = nextQ >= gs.totalQuestions;

    if (done) {
      set({ gameSession: { ...gs, score: newScore, status: 'completed', currentQuestion: nextQ } });
      return { correct, correctAnswer, done: true };
    }

    // Load next question
    if (gs.type === 'quiz') {
      const questions = (get() as { _quizQuestions?: typeof quizQuestions })._quizQuestions || [];

      const q = questions[nextQ];
      if (q) {
        set({
          gameSession: {
            ...gs, score: newScore, currentQuestion: nextQ,
            quizData: { question: q.question, options: q.options, correctIndex: q.correctIndex },
          },
        });
      }
    } else if (gs.type === 'word') {
      const puzzles = (get() as { _wordPuzzles?: typeof wordPuzzles })._wordPuzzles || [];

      const p = puzzles[nextQ];
      if (p) {
        set({
          gameSession: { ...gs, score: newScore, currentQuestion: nextQ, wordData: { scrambled: p.scrambled, answer: p.answer, hint: p.hint } },
        });
      }
    } else if (gs.type === 'memory') {
      const cards = shuffle(memoryPairs).slice(0, 3 + Math.min(nextQ, 2));
      set({
        gameSession: {
          ...gs, score: newScore, currentQuestion: nextQ,
          memoryData: { sequence: cards, revealed: true },
        },
      });
      setTimeout(() => {
        const current = get().gameSession;
        if (current.type === 'memory' && current.memoryData?.revealed) {
          set({ gameSession: { ...current, memoryData: { ...current.memoryData!, revealed: false } } });
        }
      }, 4000);
    }

    return { correct, correctAnswer, done: false };
  },

  endGame: () => set({ gameSession: { ...defaultGameSession } }),

  // === MUSIC ACTIONS ===
  playMusic: (genre) => {
    const filtered = genre ? musicLibrary.filter(t => t.genre === genre) : musicLibrary;
    const tracks = shuffle(filtered.length > 0 ? filtered : musicLibrary);
    const [current, ...queue] = tracks;
    set({ musicPlayer: { status: 'playing', currentTrack: current, queue } });
  },

  toggleMusicPlayback: () =>
    set(s => ({
      musicPlayer: {
        ...s.musicPlayer,
        status: s.musicPlayer.status === 'playing' ? 'paused' : 'playing',
      },
    })),

  nextTrack: () =>
    set(s => {
      if (s.musicPlayer.queue.length === 0) return { musicPlayer: { ...defaultMusicPlayer } };
      const [next, ...rest] = s.musicPlayer.queue;
      return { musicPlayer: { status: 'playing', currentTrack: next, queue: rest } };
    }),

  prevTrack: () =>
    set(s => {
      // Just restart current track (no history tracking)
      return { musicPlayer: { ...s.musicPlayer } };
    }),

  stopMusic: () => set({ musicPlayer: { ...defaultMusicPlayer } }),
}));
