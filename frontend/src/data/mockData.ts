import { User, ElderProfile, FamilyProfile, Reminder, VitalSign, MoodEntry, ChatMessage, Alert, SmartDevice, CheckInSession, ActivityEvent, RPMDevice, EmergencyContact, FamilyContact } from '@/types';

export const mockUsers: { email: string; password: string; user: ElderProfile | FamilyProfile }[] = [
  {
    email: 'elder@example.com',
    password: 'elder123',
    user: {
      id: 'elder-1',
      email: 'elder@example.com',
      name: 'Margaret Johnson',
      role: 'elder',
      age: 78,
      phone: '+1-555-0101',
      conditions: ['Hypertension', 'Type 2 Diabetes', 'Mild Arthritis'],
      createdAt: '2024-01-15',
      emergencyContacts: [
        { id: 'ec-1', name: 'Sarah Johnson', phone: '+1-555-0201', relationship: 'Daughter', isPrimary: true },
        { id: 'ec-2', name: 'Dr. Williams', phone: '+1-555-0301', relationship: 'Physician', isPrimary: false },
      ],
      linkedFamily: [
        { familyId: 'family-1', name: 'Sarah Johnson', relationship: 'Daughter', status: 'linked', invitedAt: '2024-01-20' },
        { familyId: 'family-2', name: 'Michael Johnson', relationship: 'Son', status: 'accepted', invitedAt: '2024-02-10' },
        { familyId: 'family-3', name: 'Emily Davis', relationship: 'Granddaughter', status: 'pending', invitedAt: '2024-03-01' },
      ],
      wellnessStars: 247,
      streak: 12,
    },
  },
  {
    email: 'family@example.com',
    password: 'family123',
    user: {
      id: 'family-1',
      email: 'family@example.com',
      name: 'Sarah Johnson',
      role: 'family',
      relationship: 'Daughter',
      phone: '+1-555-0201',
      createdAt: '2024-01-20',
      linkedElders: [
        { elderId: 'elder-1', name: 'Margaret Johnson', relationship: 'Mother', status: 'online', lastActive: new Date().toISOString(), riskLevel: 'low' },
        { elderId: 'elder-2', name: 'Robert Johnson', relationship: 'Father', status: 'offline', lastActive: new Date(Date.now() - 3600000).toISOString(), riskLevel: 'moderate' },
      ],
    },
  },
];

const now = new Date();
const h = (offset: number) => new Date(now.getTime() + offset * 3600000).toISOString();
const m = (offset: number) => new Date(now.getTime() + offset * 60000).toISOString();

export const mockReminders: Reminder[] = [
  { id: 'r1', type: 'medication', title: 'Metformin 500mg', description: 'Take with breakfast', time: h(0.5), status: 'upcoming', priority: 'high', recurring: true },
  { id: 'r2', type: 'medication', title: 'Lisinopril 10mg', description: 'Blood pressure medicine', time: h(-2), status: 'completed', priority: 'high', recurring: true },
  { id: 'r3', type: 'hydration', title: 'Drink Water', description: 'Stay hydrated — glass of water', time: h(1), status: 'upcoming', priority: 'medium', recurring: true },
  { id: 'r4', type: 'movement', title: 'Gentle Walk', description: '10-minute walk around the house', time: h(2), status: 'upcoming', priority: 'medium', recurring: true },
  { id: 'r5', type: 'appointment', title: 'Dr. Williams Checkup', description: 'Regular checkup appointment', time: h(48), status: 'upcoming', priority: 'high', recurring: false },
  { id: 'r6', type: 'medication', title: 'Evening Vitamins', description: 'Vitamin D + Calcium', time: h(-5), status: 'missed', priority: 'medium', recurring: true },
  { id: 'r7', type: 'hydration', title: 'Afternoon Tea', description: 'Warm herbal tea', time: h(3), status: 'upcoming', priority: 'low', recurring: true },
];

export const mockVitals: VitalSign[] = [
  { id: 'v1', type: 'heart_rate', value: 72, unit: 'bpm', timestamp: m(-5), status: 'normal', trend: 'stable' },
  { id: 'v2', type: 'blood_pressure', value: '138/82', unit: 'mmHg', timestamp: m(-15), status: 'warning', trend: 'up' },
  { id: 'v3', type: 'glucose', value: 142, unit: 'mg/dL', timestamp: m(-30), status: 'warning', trend: 'up' },
  { id: 'v4', type: 'activity', value: 3420, unit: 'steps', timestamp: m(-10), status: 'normal', trend: 'stable' },
  { id: 'v5', type: 'spo2', value: 97, unit: '%', timestamp: m(-8), status: 'normal', trend: 'stable' },
  { id: 'v6', type: 'temperature', value: 98.4, unit: '°F', timestamp: m(-20), status: 'normal', trend: 'stable' },
];

export const mockMoodHistory: MoodEntry[] = [
  { id: 'm1', mood: 'happy', score: 8, note: 'Had a lovely video call with Sarah', timestamp: h(-2), sentiment: 'positive' },
  { id: 'm2', mood: 'calm', score: 7, note: 'Enjoyed morning tea in the garden', timestamp: h(-26), sentiment: 'positive' },
  { id: 'm3', mood: 'lonely', score: 3, note: 'Nobody visited today, feeling isolated', timestamp: h(-50), sentiment: 'negative', triggers: ['isolation'] },
  { id: 'm4', mood: 'neutral', score: 5, note: 'Regular day, nothing special', timestamp: h(-74), sentiment: 'neutral' },
  { id: 'm5', mood: 'anxious', score: 3, note: 'Worried about upcoming doctor appointment', timestamp: h(-98), sentiment: 'negative', triggers: ['health_anxiety'] },
  { id: 'm6', mood: 'happy', score: 9, note: 'Grandkids came to visit!', timestamp: h(-122), sentiment: 'positive' },
  { id: 'm7', mood: 'sad', score: 2, note: 'Missing Harold today', timestamp: h(-146), sentiment: 'risk', triggers: ['grief', 'loneliness'] },
];

export const mockChatHistory: ChatMessage[] = [
  { id: 'c1', role: 'assistant', content: 'Good morning, Margaret! ☀️ How are you feeling today?', timestamp: h(-1), tags: ['greeting'] },
  { id: 'c2', role: 'user', content: 'Good morning! I slept well, feeling good today.', timestamp: h(-0.95) },
  { id: 'c3', role: 'assistant', content: "That's wonderful to hear! You have your Metformin coming up in about 30 minutes. Would you like me to remind you?", timestamp: h(-0.9), intent: 'medication_reminder', tags: ['medication'] },
  { id: 'c4', role: 'user', content: 'Yes please, remind me when it\'s time.', timestamp: h(-0.85) },
  { id: 'c5', role: 'assistant', content: "I'll remind you! By the way, you've been on a 12-day wellness streak — amazing! 🌟 Would you like to do a quick morning check-in?", timestamp: h(-0.8), tags: ['wellness', 'checkin'] },
];

export const mockAlerts: Alert[] = [
  { id: 'a1', type: 'vitals', severity: 'medium', title: 'Elevated Blood Pressure', description: 'BP reading 138/82 — slightly above normal range', timestamp: m(-15), status: 'active', elderName: 'Margaret Johnson', recommendedAction: 'Monitor next reading, contact physician if persists' },
  { id: 'a2', type: 'medication', severity: 'high', title: 'Missed Evening Vitamins', description: 'Vitamin D + Calcium was not taken at scheduled time', timestamp: h(-5), status: 'active', elderName: 'Margaret Johnson', recommendedAction: 'Send voice reminder, check in with elder' },
  { id: 'a3', type: 'vitals', severity: 'medium', title: 'Glucose Trending Up', description: 'Glucose at 142 mg/dL, above target range of 130', timestamp: m(-30), status: 'acknowledged', elderName: 'Margaret Johnson', recommendedAction: 'Review diet, confirm medication adherence' },
  { id: 'a4', type: 'mood', severity: 'low', title: 'Loneliness Pattern Detected', description: 'Two low mood entries this week mentioning isolation', timestamp: h(-50), status: 'active', elderName: 'Margaret Johnson', recommendedAction: 'Schedule family video call, activate engagement activities' },
  { id: 'a5', type: 'inactivity', severity: 'low', title: 'Low Activity Today', description: 'Only 3,420 steps recorded, below 5,000 goal', timestamp: m(-10), status: 'active', elderName: 'Margaret Johnson', recommendedAction: 'Suggest gentle walk or mobility exercise' },
];

export const mockSmartDevices: SmartDevice[] = [
  { id: 'sd1', name: 'Living Room Light', type: 'light', status: 'on', room: 'Living Room', lastUpdated: m(-5) },
  { id: 'sd2', name: 'Bedroom Light', type: 'light', status: 'off', room: 'Bedroom', lastUpdated: m(-60) },
  { id: 'sd3', name: 'Front Door Lock', type: 'lock', status: 'locked', room: 'Entrance', lastUpdated: m(-120) },
  { id: 'sd4', name: 'Back Door', type: 'door', status: 'closed', room: 'Kitchen', lastUpdated: m(-30) },
  { id: 'sd5', name: 'Smart Thermostat', type: 'thermostat', status: 'on', room: 'Hallway', value: 72, lastUpdated: m(-10) },
  { id: 'sd6', name: 'Bathroom Light', type: 'light', status: 'off', room: 'Bathroom', lastUpdated: m(-90) },
];

export const mockCheckIn: CheckInSession = {
  id: 'ci-today',
  date: new Date().toISOString().split('T')[0],
  status: 'pending',
  questions: [
    { id: 'q1', category: 'mood', question: 'How are you feeling emotionally right now?' },
    { id: 'q2', category: 'memory', question: 'Can you tell me what you had for breakfast today?' },
    { id: 'q3', category: 'mobility', question: 'Have you been able to move around comfortably today?' },
    { id: 'q4', category: 'medication', question: 'Have you taken all your morning medicines?' },
    { id: 'q5', category: 'hydration', question: 'How many glasses of water have you had so far?' },
    { id: 'q6', category: 'safety', question: 'Do you feel safe and comfortable in your home right now?' },
  ],
  overallScore: undefined,
  summary: undefined,
};

export const mockActivityTimeline: ActivityEvent[] = [
  { id: 'at1', type: 'medication_taken', title: 'Lisinopril Taken', description: 'Blood pressure medication taken on time', timestamp: h(-2), category: 'medication' },
  { id: 'at2', type: 'mood_log', title: 'Mood Logged: Happy', description: 'Had a lovely video call with Sarah', timestamp: h(-2), category: 'mood' },
  { id: 'at3', type: 'hydration', title: 'Water Consumed', description: 'Drank a glass of water', timestamp: h(-3), category: 'hydration' },
  { id: 'at4', type: 'smart_home', title: 'Living Room Light On', description: 'Light turned on automatically at sunset', timestamp: h(-4), category: 'smart_home' },
  { id: 'at5', type: 'exercise', title: 'Morning Stretches', description: 'Completed 5-minute gentle stretching', timestamp: h(-5), category: 'exercise' },
  { id: 'at6', type: 'vitals', title: 'Vitals Recorded', description: 'Heart rate: 72 bpm, SpO2: 97%', timestamp: h(-5), category: 'vitals' },
  { id: 'at7', type: 'medication_missed', title: 'Evening Vitamins Missed', description: 'Vitamin D + Calcium not taken', timestamp: h(-5), category: 'medication' },
  { id: 'at8', type: 'intervention', title: 'Calming Music Played', description: 'Triggered after detecting mild anxiety', timestamp: h(-24), category: 'intervention' },
  { id: 'at9', type: 'checkin', title: 'Daily Check-in Completed', description: 'Score: 7.5/10 — Good overall health', timestamp: h(-24), category: 'checkin' },
  { id: 'at10', type: 'alert', title: 'Fall Risk Warning', description: 'Unusual movement pattern detected', timestamp: h(-48), category: 'alert' },
];

export const mockRPMDevices: RPMDevice[] = [
  { id: 'rpm1', name: 'Pulse Oximeter', type: 'SpO2 + Heart Rate', connected: true, battery: 85, lastSync: m(-8), anomaly: false },
  { id: 'rpm2', name: 'Blood Pressure Monitor', type: 'BP Cuff', connected: true, battery: 62, lastSync: m(-15), anomaly: true },
  { id: 'rpm3', name: 'Glucose Monitor', type: 'CGM', connected: true, battery: 45, lastSync: m(-30), anomaly: true },
  { id: 'rpm4', name: 'Activity Tracker', type: 'Wrist Wearable', connected: true, battery: 78, lastSync: m(-10), anomaly: false },
  { id: 'rpm5', name: 'Fall Detector', type: 'Pendant Sensor', connected: true, battery: 91, lastSync: m(-3), anomaly: false },
];

export const mockVitalsHistory = {
  heart_rate: Array.from({ length: 24 }, (_, i) => ({ time: `${i}:00`, value: 68 + Math.floor(Math.random() * 12) })),
  blood_pressure_sys: Array.from({ length: 7 }, (_, i) => ({ day: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i], value: 125 + Math.floor(Math.random() * 20) })),
  glucose: Array.from({ length: 7 }, (_, i) => ({ day: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i], value: 110 + Math.floor(Math.random() * 40) })),
  activity: Array.from({ length: 7 }, (_, i) => ({ day: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i], value: 2000 + Math.floor(Math.random() * 5000) })),
};

export const mockFamilyContacts: FamilyContact[] = [
  { id: 'fc-1', name: 'Sarah Johnson', relationship: 'Daughter', phone: '+1-555-0201', isPrimary: true, aliases: ['sarah', 'daughter', 'my daughter'], available: true },
  { id: 'fc-2', name: 'Michael Johnson', relationship: 'Son', phone: '+1-555-0202', isPrimary: false, aliases: ['michael', 'mike', 'son', 'my son'], available: true },
  { id: 'fc-3', name: 'Emily Davis', relationship: 'Granddaughter', phone: '+1-555-0203', isPrimary: false, aliases: ['emily', 'granddaughter', 'my granddaughter'], available: false },
  { id: 'fc-4', name: 'Dr. Williams', relationship: 'Physician', phone: '+1-555-0301', isPrimary: false, aliases: ['doctor', 'dr williams', 'physician', 'my doctor'], available: true },
  { id: 'fc-5', name: 'Maria Garcia', relationship: 'Caregiver', phone: '+1-555-0401', isPrimary: false, aliases: ['maria', 'caregiver', 'my caregiver', 'nurse'], available: true },
];
