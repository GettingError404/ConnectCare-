export type UserRole = 'elder' | 'family' | 'caregiver' | 'admin';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar?: string;
  phone?: string;
  createdAt: string;
  age?: number;
  conditions?: string[];
  emergencyContacts?: EmergencyContact[];
  linkedFamily?: FamilyLink[];
  wellnessStars?: number;
  streak?: number;
}


export interface ElderProfile extends User {
  role: 'elder';
  age: number;
  conditions: string[];
  emergencyContacts: EmergencyContact[];
  linkedFamily: FamilyLink[];
  wellnessStars: number;
  streak: number;
}

export interface FamilyProfile extends User {
  role: 'family';
  relationship: string;
  linkedElders: ElderLink[];
}

export interface FamilyLink {
  familyId: string;
  name: string;
  relationship: string;
  status: 'pending' | 'accepted' | 'linked';
  invitedAt: string;
}

export interface ElderLink {
  elderId: string;
  name: string;
  relationship: string;
  status: 'online' | 'offline';
  lastActive: string;
  riskLevel: 'low' | 'moderate' | 'high';
  avatar?: string;
}

export interface EmergencyContact {
  id: string;
  name: string;
  phone: string;
  relationship: string;
  isPrimary: boolean;
}

export interface Reminder {
  id: string;
  type: 'medication' | 'hydration' | 'appointment' | 'movement';
  title: string;
  description: string;
  time: string;
  status: 'upcoming' | 'missed' | 'completed' | 'snoozed';
  priority: 'low' | 'medium' | 'high';
  recurring: boolean;
}

export interface VitalSign {
  id: string;
  type: 'heart_rate' | 'blood_pressure' | 'glucose' | 'activity' | 'spo2' | 'temperature';
  value: number | string;
  unit: string;
  timestamp: string;
  status: 'normal' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
}

export interface MoodEntry {
  id: string;
  mood: 'happy' | 'calm' | 'neutral' | 'sad' | 'anxious' | 'lonely' | 'frustrated' | 'angry';
  score: number; // 1-10
  note: string;
  timestamp: string;
  sentiment: 'positive' | 'neutral' | 'negative' | 'risk';
  triggers?: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
  tags?: string[];
}

export interface Alert {
  id: string;
  type: 'vitals' | 'medication' | 'mood' | 'inactivity' | 'fall' | 'emergency' | 'checkin' | 'cognitive';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  timestamp: string;
  status: 'active' | 'acknowledged' | 'resolved' | 'escalated';
  elderName: string;
  recommendedAction: string;
}

export interface SmartDevice {
  id: string;
  name: string;
  type: 'light' | 'lock' | 'door' | 'thermostat';
  status: 'on' | 'off' | 'locked' | 'unlocked' | 'open' | 'closed';
  room: string;
  value?: number;
  lastUpdated: string;
}

export interface CheckInQuestion {
  id: string;
  category: 'mood' | 'memory' | 'mobility' | 'medication' | 'hydration' | 'safety';
  question: string;
  answer?: string;
  score?: number;
}

export interface CheckInSession {
  id: string;
  date: string;
  status: 'pending' | 'in_progress' | 'completed';
  questions: CheckInQuestion[];
  overallScore?: number;
  summary?: string;
}

export interface ActivityEvent {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  category: 'medication' | 'hydration' | 'mood' | 'checkin' | 'exercise' | 'intervention' | 'smart_home' | 'alert' | 'emergency' | 'vitals';
  icon?: string;
}

export interface WellnessReward {
  id: string;
  action: string;
  stars: number;
  timestamp: string;
}

export interface EmergencyState {
  active: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  triggeredAt?: string;
  triggeredBy?: 'voice' | 'button' | 'fall_detection' | 'vitals';
  status?: 'triggered' | 'family_notified' | 'help_requested' | 'resolved';
  updates: { message: string; timestamp: string }[];
}

export interface RPMDevice {
  id: string;
  name: string;
  type: string;
  connected: boolean;
  battery: number;
  lastSync: string;
  anomaly: boolean;
}

export interface FamilyContact {
  id: string;
  name: string;
  relationship: string;
  phone: string;
  isPrimary: boolean;
  aliases: string[]; // e.g. ['son', 'michael', 'mike']
  available: boolean;
}

export type CallStatus = 'idle' | 'calling' | 'connected' | 'failed' | 'ended' | 'cancelled';

export interface CallState {
  status: CallStatus;
  contactId?: string;
  contactName?: string;
  startedAt?: string;
  duration?: number;
}

// Caregiver types
export interface CaregiverProfile extends User {
  role: 'caregiver';
  title: string; // Doctor, Nurse, Health Worker
  specialty?: string;
  licenseNumber?: string;
  assignedElders: CaregiverElderLink[];
}

export interface CaregiverElderLink {
  elderId: string;
  name: string;
  age: number;
  conditions: string[];
  riskLevel: 'low' | 'moderate' | 'high' | 'critical';
  status: 'online' | 'offline';
  lastActive: string;
  avatar?: string;
  medicationAdherence: number; // 0-100
  moodTrend: 'improving' | 'stable' | 'declining';
  lastCheckIn: string;
  cognitiveScore: number; // 0-100
}

export interface CareTask {
  id: string;
  elderId: string;
  elderName: string;
  type: 'medication' | 'check_in' | 'follow_up' | 'assessment' | 'telehealth' | 'lab_review';
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'in_progress' | 'completed' | 'overdue';
  dueDate: string;
  assignedTo: string;
  completedAt?: string;
  notes?: string;
}

export interface AWVRecord {
  elderId: string;
  elderName: string;
  lastVisitDate: string;
  nextDueDate: string;
  status: 'completed' | 'due_soon' | 'overdue' | 'scheduled';
  healthRiskAssessment: boolean;
  depressionScreening: boolean;
  cognitiveAssessment: boolean;
  fallRiskAssessment: boolean;
  advanceCarePlanning: boolean;
  medicationReconciliation: boolean;
  score: number; // compliance score 0-100
}

export interface ChronicCareRecord {
  elderId: string;
  elderName: string;
  condition: string;
  treatmentPlan: string;
  adherence: number; // 0-100
  lastReview: string;
  nextReview: string;
  status: 'on_track' | 'at_risk' | 'non_compliant';
  alerts: string[];
}

export interface AlertHistoryEntry {
  id: string;
  alertId: string;
  action: string;
  performedBy: string;
  timestamp: string;
  notes?: string;
}

// Game types
export type GameType = 'quiz' | 'memory' | 'word';

export interface GameSession {
  type: GameType;
  status: 'idle' | 'active' | 'completed';
  currentQuestion: number;
  totalQuestions: number;
  score: number;
  quizData?: { question: string; options: string[]; correctIndex: number };
  memoryData?: { sequence: { emoji: string; label: string }[]; revealed: boolean };
  wordData?: { scrambled: string; answer: string; hint: string };
}

// Music player types
export interface MusicPlayerState {
  status: 'idle' | 'playing' | 'paused';
  currentTrack: { id: string; title: string; artist: string; genre: string; duration: number } | null;
  queue: { id: string; title: string; artist: string; genre: string; duration: number }[];
}
