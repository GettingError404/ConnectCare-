import { Alert, CareTask, AWVRecord, ChronicCareRecord, AlertHistoryEntry, CaregiverElderLink, VitalSign, MoodEntry, CaregiverProfile } from '@/types';

const now = new Date();
const h = (offset: number) => new Date(now.getTime() + offset * 3600000).toISOString();
const m = (offset: number) => new Date(now.getTime() + offset * 60000).toISOString();
const d = (offset: number) => new Date(now.getTime() + offset * 86400000).toISOString();

export const mockCaregiverUser: { email: string; password: string; user: CaregiverProfile } = {
  email: 'caregiver@example.com',
  password: 'care123',
  user: {
    id: 'caregiver-1',
    email: 'caregiver@example.com',
    name: 'Dr. Amanda Smith',
    role: 'caregiver',
    title: 'Primary Care Physician',
    specialty: 'Geriatric Medicine',
    licenseNumber: 'MD-2024-5678',
    createdAt: '2024-01-01',
    assignedElders: [],
  },
};

export const mockCaregiverElders: CaregiverElderLink[] = [
  { elderId: 'elder-1', name: 'Margaret Johnson', age: 78, conditions: ['Hypertension', 'Type 2 Diabetes', 'Mild Arthritis'], riskLevel: 'moderate', status: 'online', lastActive: m(-5), medicationAdherence: 82, moodTrend: 'stable', lastCheckIn: h(-2), cognitiveScore: 78 },
  { elderId: 'elder-2', name: 'Robert Wilson', age: 84, conditions: ['COPD', 'Heart Failure', 'Depression'], riskLevel: 'high', status: 'offline', lastActive: h(-3), medicationAdherence: 61, moodTrend: 'declining', lastCheckIn: h(-26), cognitiveScore: 62 },
  { elderId: 'elder-3', name: 'Dorothy Chen', age: 72, conditions: ['Osteoporosis', 'Anxiety'], riskLevel: 'low', status: 'online', lastActive: m(-15), medicationAdherence: 95, moodTrend: 'improving', lastCheckIn: h(-1), cognitiveScore: 91 },
  { elderId: 'elder-4', name: 'James Brown', age: 81, conditions: ['Parkinson\'s', 'Hypertension', 'Chronic Pain'], riskLevel: 'critical', status: 'offline', lastActive: h(-8), medicationAdherence: 45, moodTrend: 'declining', lastCheckIn: h(-50), cognitiveScore: 48 },
  { elderId: 'elder-5', name: 'Helen Martinez', age: 76, conditions: ['Type 1 Diabetes', 'Neuropathy'], riskLevel: 'moderate', status: 'online', lastActive: m(-30), medicationAdherence: 74, moodTrend: 'stable', lastCheckIn: h(-4), cognitiveScore: 85 },
];

export const mockCaregiverAlerts: Alert[] = [
  { id: 'ca1', type: 'vitals', severity: 'critical', title: 'Irregular Heart Rate – James Brown', description: 'Heart rate dropped to 48 bpm then spiked to 112 bpm within 30 minutes', timestamp: m(-12), status: 'active', elderName: 'James Brown', recommendedAction: 'Immediate telehealth call, consider ER referral' },
  { id: 'ca2', type: 'medication', severity: 'high', title: 'Repeated Missed Medications – Robert Wilson', description: '3 consecutive doses of heart failure medication missed', timestamp: h(-2), status: 'active', elderName: 'Robert Wilson', recommendedAction: 'Contact family, schedule urgent check-in' },
  { id: 'ca3', type: 'mood', severity: 'high', title: 'Depression Risk Escalation – Robert Wilson', description: 'Mood scores declining for 5 consecutive days, isolation detected', timestamp: h(-6), status: 'active', elderName: 'Robert Wilson', recommendedAction: 'Psychiatric consult referral, increase check-in frequency' },
  { id: 'ca4', type: 'fall', severity: 'medium', title: 'Fall Risk Elevated – James Brown', description: 'Gait analysis shows 40% increased fall probability', timestamp: h(-4), status: 'active', elderName: 'James Brown', recommendedAction: 'Physical therapy referral, home safety assessment' },
  { id: 'ca5', type: 'vitals', severity: 'medium', title: 'Blood Glucose Spike – Helen Martinez', description: 'Post-meal glucose reading 245 mg/dL, above target of 180', timestamp: h(-1), status: 'active', elderName: 'Helen Martinez', recommendedAction: 'Review insulin dosing, dietary counseling' },
  { id: 'ca6', type: 'inactivity', severity: 'low', title: 'Low Activity – Margaret Johnson', description: 'Only 2,100 steps today vs 5,000 goal', timestamp: h(-3), status: 'acknowledged', elderName: 'Margaret Johnson', recommendedAction: 'Encourage gentle exercise via voice companion' },
  { id: 'ca7', type: 'cognitive', severity: 'medium', title: 'Cognitive Score Drop – James Brown', description: 'Weekly cognitive assessment dropped from 55 to 48', timestamp: h(-24), status: 'active', elderName: 'James Brown', recommendedAction: 'Schedule neurology follow-up' },
  { id: 'ca8', type: 'medication', severity: 'low', title: 'Late Medication – Dorothy Chen', description: 'Calcium supplement taken 2 hours late', timestamp: h(-5), status: 'resolved', elderName: 'Dorothy Chen', recommendedAction: 'Monitor, no immediate action needed' },
];

export const mockCareTasks: CareTask[] = [
  { id: 'ct1', elderId: 'elder-4', elderName: 'James Brown', type: 'telehealth', title: 'Urgent Vitals Review', description: 'Review irregular heart rate pattern and adjust medication', priority: 'urgent', status: 'pending', dueDate: h(1), assignedTo: 'Dr. Amanda Smith' },
  { id: 'ct2', elderId: 'elder-2', elderName: 'Robert Wilson', type: 'check_in', title: 'Depression Assessment', description: 'Conduct PHQ-9 depression screening', priority: 'high', status: 'pending', dueDate: h(4), assignedTo: 'Dr. Amanda Smith' },
  { id: 'ct3', elderId: 'elder-5', elderName: 'Helen Martinez', type: 'medication', title: 'Insulin Dose Adjustment', description: 'Review glucose logs and adjust basal insulin', priority: 'high', status: 'in_progress', dueDate: h(6), assignedTo: 'Dr. Amanda Smith' },
  { id: 'ct4', elderId: 'elder-1', elderName: 'Margaret Johnson', type: 'follow_up', title: 'BP Medication Follow-up', description: 'Review blood pressure trends after Lisinopril adjustment', priority: 'medium', status: 'pending', dueDate: d(2), assignedTo: 'Dr. Amanda Smith' },
  { id: 'ct5', elderId: 'elder-3', elderName: 'Dorothy Chen', type: 'assessment', title: 'Fall Risk Assessment', description: 'Quarterly fall risk screening and home safety review', priority: 'medium', status: 'pending', dueDate: d(5), assignedTo: 'Dr. Amanda Smith' },
  { id: 'ct6', elderId: 'elder-4', elderName: 'James Brown', type: 'lab_review', title: 'Blood Work Review', description: 'Review latest CBC and metabolic panel results', priority: 'high', status: 'pending', dueDate: d(1), assignedTo: 'Dr. Amanda Smith' },
  { id: 'ct7', elderId: 'elder-1', elderName: 'Margaret Johnson', type: 'check_in', title: 'Weekly Check-in', description: 'Routine weekly wellness check-in call', priority: 'low', status: 'completed', dueDate: h(-48), assignedTo: 'Dr. Amanda Smith', completedAt: h(-46) },
  { id: 'ct8', elderId: 'elder-3', elderName: 'Dorothy Chen', type: 'medication', title: 'Anxiety Medication Review', description: 'Review effectiveness of current anxiety management', priority: 'low', status: 'completed', dueDate: h(-72), assignedTo: 'Dr. Amanda Smith', completedAt: h(-70) },
];

export const mockAWVRecords: AWVRecord[] = [
  { elderId: 'elder-1', elderName: 'Margaret Johnson', lastVisitDate: d(-90), nextDueDate: d(275), status: 'completed', healthRiskAssessment: true, depressionScreening: true, cognitiveAssessment: true, fallRiskAssessment: true, advanceCarePlanning: true, medicationReconciliation: true, score: 100 },
  { elderId: 'elder-2', elderName: 'Robert Wilson', lastVisitDate: d(-340), nextDueDate: d(25), status: 'due_soon', healthRiskAssessment: true, depressionScreening: false, cognitiveAssessment: true, fallRiskAssessment: false, advanceCarePlanning: false, medicationReconciliation: true, score: 50 },
  { elderId: 'elder-3', elderName: 'Dorothy Chen', lastVisitDate: d(-180), nextDueDate: d(185), status: 'completed', healthRiskAssessment: true, depressionScreening: true, cognitiveAssessment: true, fallRiskAssessment: true, advanceCarePlanning: false, medicationReconciliation: true, score: 83 },
  { elderId: 'elder-4', elderName: 'James Brown', lastVisitDate: d(-400), nextDueDate: d(-35), status: 'overdue', healthRiskAssessment: true, depressionScreening: false, cognitiveAssessment: false, fallRiskAssessment: false, advanceCarePlanning: false, medicationReconciliation: false, score: 17 },
  { elderId: 'elder-5', elderName: 'Helen Martinez', lastVisitDate: d(-60), nextDueDate: d(305), status: 'completed', healthRiskAssessment: true, depressionScreening: true, cognitiveAssessment: true, fallRiskAssessment: true, advanceCarePlanning: true, medicationReconciliation: true, score: 100 },
];

export const mockChronicCareRecords: ChronicCareRecord[] = [
  { elderId: 'elder-1', elderName: 'Margaret Johnson', condition: 'Hypertension', treatmentPlan: 'Lisinopril 10mg daily, low-sodium diet, weekly BP monitoring', adherence: 85, lastReview: d(-14), nextReview: d(16), status: 'on_track', alerts: [] },
  { elderId: 'elder-1', elderName: 'Margaret Johnson', condition: 'Type 2 Diabetes', treatmentPlan: 'Metformin 500mg BID, dietary management, quarterly A1C', adherence: 78, lastReview: d(-30), nextReview: d(60), status: 'on_track', alerts: ['Glucose trending up this week'] },
  { elderId: 'elder-2', elderName: 'Robert Wilson', condition: 'Heart Failure', treatmentPlan: 'Carvedilol 25mg BID, Furosemide 40mg daily, fluid restriction', adherence: 55, lastReview: d(-7), nextReview: d(7), status: 'at_risk', alerts: ['3 missed doses this week', 'Weight increase 2.5 lbs'] },
  { elderId: 'elder-2', elderName: 'Robert Wilson', condition: 'COPD', treatmentPlan: 'Tiotropium inhaler daily, pulmonary rehab', adherence: 68, lastReview: d(-21), nextReview: d(9), status: 'at_risk', alerts: ['SpO2 dropped below 92% twice'] },
  { elderId: 'elder-4', elderName: 'James Brown', condition: 'Parkinson\'s', treatmentPlan: 'Carbidopa-Levodopa 25/100 TID, physical therapy 2x/week', adherence: 42, lastReview: d(-10), nextReview: d(4), status: 'non_compliant', alerts: ['Missed 8 of last 14 doses', 'No PT sessions attended this month', 'Tremor severity increasing'] },
  { elderId: 'elder-5', elderName: 'Helen Martinez', condition: 'Type 1 Diabetes', treatmentPlan: 'Insulin glargine 22U nightly, lispro per sliding scale, CGM monitoring', adherence: 76, lastReview: d(-5), nextReview: d(25), status: 'on_track', alerts: ['2 hyperglycemic episodes this week'] },
];

export const mockAlertHistory: AlertHistoryEntry[] = [
  { id: 'ah1', alertId: 'ca8', action: 'Resolved', performedBy: 'Dr. Amanda Smith', timestamp: h(-4), notes: 'Patient confirmed supplement was taken, no concern' },
  { id: 'ah2', alertId: 'ca6', action: 'Acknowledged', performedBy: 'Dr. Amanda Smith', timestamp: h(-2), notes: 'Will follow up during next check-in' },
  { id: 'ah3', alertId: 'old-1', action: 'Escalated to ER', performedBy: 'Dr. Amanda Smith', timestamp: d(-3), notes: 'Patient reported chest pain, 911 dispatched' },
  { id: 'ah4', alertId: 'old-2', action: 'Resolved', performedBy: 'Nurse Garcia', timestamp: d(-5), notes: 'Medication dosage adjusted, vitals normalized' },
  { id: 'ah5', alertId: 'old-3', action: 'Family Notified', performedBy: 'Dr. Amanda Smith', timestamp: d(-7), notes: 'Informed daughter about mood decline pattern' },
];

const genVitals = (base: { hr: number; bp: string; glucose: number; spo2: number }): VitalSign[] => [
  { id: `v-${Math.random()}`, type: 'heart_rate', value: base.hr + Math.floor(Math.random() * 10 - 5), unit: 'bpm', timestamp: m(-5), status: base.hr > 95 || base.hr < 55 ? 'warning' : 'normal', trend: 'stable' },
  { id: `v-${Math.random()}`, type: 'blood_pressure', value: base.bp, unit: 'mmHg', timestamp: m(-15), status: parseInt(base.bp) > 140 ? 'warning' : 'normal', trend: 'stable' },
  { id: `v-${Math.random()}`, type: 'glucose', value: base.glucose, unit: 'mg/dL', timestamp: m(-30), status: base.glucose > 180 ? 'critical' : base.glucose > 140 ? 'warning' : 'normal', trend: base.glucose > 160 ? 'up' : 'stable' },
  { id: `v-${Math.random()}`, type: 'spo2', value: base.spo2, unit: '%', timestamp: m(-8), status: base.spo2 < 94 ? 'warning' : 'normal', trend: 'stable' },
];

export const mockCaregiverVitalsMap: Record<string, VitalSign[]> = {
  'elder-1': genVitals({ hr: 72, bp: '138/82', glucose: 142, spo2: 97 }),
  'elder-2': genVitals({ hr: 88, bp: '155/95', glucose: 118, spo2: 91 }),
  'elder-3': genVitals({ hr: 68, bp: '120/78', glucose: 105, spo2: 98 }),
  'elder-4': genVitals({ hr: 52, bp: '148/90', glucose: 132, spo2: 94 }),
  'elder-5': genVitals({ hr: 76, bp: '130/85', glucose: 245, spo2: 96 }),
};

export const mockCaregiverMoodMap: Record<string, MoodEntry[]> = {
  'elder-1': [
    { id: 'cm1', mood: 'happy', score: 8, note: 'Good day', timestamp: h(-2), sentiment: 'positive' },
    { id: 'cm2', mood: 'calm', score: 7, note: 'Relaxed morning', timestamp: h(-26), sentiment: 'positive' },
  ],
  'elder-2': [
    { id: 'cm3', mood: 'sad', score: 3, note: 'Feeling isolated', timestamp: h(-4), sentiment: 'negative', triggers: ['isolation'] },
    { id: 'cm4', mood: 'anxious', score: 2, note: 'Breathing difficulty worries', timestamp: h(-28), sentiment: 'risk', triggers: ['health_anxiety'] },
  ],
  'elder-3': [
    { id: 'cm5', mood: 'happy', score: 9, note: 'Great day with family', timestamp: h(-1), sentiment: 'positive' },
  ],
  'elder-4': [
    { id: 'cm6', mood: 'frustrated', score: 2, note: 'Can\'t do things anymore', timestamp: h(-6), sentiment: 'risk', triggers: ['disability'] },
    { id: 'cm7', mood: 'angry', score: 2, note: 'Dropped things again', timestamp: h(-30), sentiment: 'negative' },
  ],
  'elder-5': [
    { id: 'cm8', mood: 'neutral', score: 5, note: 'Average day', timestamp: h(-3), sentiment: 'neutral' },
  ],
};
