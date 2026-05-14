import { create } from 'zustand';
import { Alert, CareTask, AWVRecord, ChronicCareRecord, AlertHistoryEntry, CaregiverElderLink, VitalSign, MoodEntry } from '@/types';
import { alertsService, type BackendAlert } from '@/lib/api/services/alerts';
import { healthcareService } from '@/lib/api/services/healthcare';
import { telemetryService } from '@/lib/api/services/telemetry';

type ElderRecord = {
  id: string;
  name: string;
  age: number;
  conditions: string[];
  riskLevel: CaregiverElderLink['riskLevel'];
  status: CaregiverElderLink['status'];
  lastActive: string;
  medicationAdherence: number;
  moodTrend: CaregiverElderLink['moodTrend'];
  lastCheckIn: string;
  cognitiveScore: number;
  avatar?: string;
};

function mapSeverityToRisk(severity: string): CaregiverElderLink['riskLevel'] {
  if (severity === 'critical') return 'critical';
  if (severity === 'high') return 'high';
  if (severity === 'medium') return 'moderate';
  return 'low';
}

function mapBackendAlert(alert: BackendAlert, elderName = 'Assigned patient'): Alert {
  return {
    id: alert.id,
    type: alert.alert_type.includes('med') ? 'medication' : alert.alert_type.includes('fall') ? 'fall' : alert.alert_type.includes('mood') ? 'mood' : 'vitals',
    severity: alert.severity as Alert['severity'],
    title: alert.alert_type.replace(/_/g, ' '),
    description: alert.message,
    timestamp: alert.created_at,
    status: alert.is_resolved ? 'resolved' : 'active',
    elderName,
    recommendedAction: alert.is_resolved ? 'No action required' : 'Review the alert and follow up',
  };
}

function mapTelemetryToVitals(readings: { id: string; recorded_at: string; heart_rate?: number | null; spo2?: number | null; systolic_bp?: number | null; diastolic_bp?: number | null; glucose_level?: number | null; body_temperature?: number | null }[]): VitalSign[] {
  return readings.flatMap(reading => {
    const timestamp = reading.recorded_at;
    const mapped: VitalSign[] = [];
    if (typeof reading.heart_rate === 'number') mapped.push({ id: `hr-${reading.id}`, type: 'heart_rate', value: reading.heart_rate, unit: 'bpm', timestamp, status: reading.heart_rate >= 100 ? 'warning' : 'normal', trend: 'stable' });
    if (typeof reading.spo2 === 'number') mapped.push({ id: `spo2-${reading.id}`, type: 'spo2', value: reading.spo2, unit: '%', timestamp, status: reading.spo2 < 95 ? 'warning' : 'normal', trend: 'stable' });
    if (typeof reading.glucose_level === 'number') mapped.push({ id: `glucose-${reading.id}`, type: 'glucose', value: reading.glucose_level, unit: 'mg/dL', timestamp, status: reading.glucose_level > 140 ? 'warning' : 'normal', trend: 'stable' });
    if (typeof reading.body_temperature === 'number') mapped.push({ id: `temp-${reading.id}`, type: 'temperature', value: reading.body_temperature, unit: '°F', timestamp, status: reading.body_temperature > 99.5 ? 'warning' : 'normal', trend: 'stable' });
    if (typeof reading.systolic_bp === 'number' && typeof reading.diastolic_bp === 'number') mapped.push({ id: `bp-${reading.id}`, type: 'blood_pressure', value: `${reading.systolic_bp}/${reading.diastolic_bp}`, unit: 'mmHg', timestamp, status: reading.systolic_bp >= 130 || reading.diastolic_bp >= 80 ? 'warning' : 'normal', trend: 'stable' });
    return mapped;
  });
}

function buildElderRecord(id: string, name: string, age: number, conditions: string[], riskLevel: CaregiverElderLink['riskLevel'], lastActive: string): CaregiverElderLink {
  return {
    elderId: id,
    name,
    age,
    conditions,
    riskLevel,
    status: new Date(lastActive).getTime() > Date.now() - 1000 * 60 * 60 * 4 ? 'online' : 'offline',
    lastActive,
    avatar: undefined,
    medicationAdherence: 100 - Math.min(45, conditions.length * 8),
    moodTrend: riskLevel === 'critical' || riskLevel === 'high' ? 'declining' : 'stable',
    lastCheckIn: lastActive,
    cognitiveScore: 100 - Math.min(40, conditions.length * 10),
  };
}

interface CaregiverState {
  assignedElders: CaregiverElderLink[];
  selectedElderId: string | null;
  alerts: Alert[];
  alertHistory: AlertHistoryEntry[];
  tasks: CareTask[];
  awvRecords: AWVRecord[];
  chronicCare: ChronicCareRecord[];
  elderVitals: Record<string, VitalSign[]>;
  elderMoods: Record<string, MoodEntry[]>;
  isLoading: boolean;

  loadDashboardData: () => Promise<void>;
  setSelectedElder: (id: string | null) => void;
  updateAlertStatus: (id: string, status: Alert['status'], notes?: string) => void;
  updateTaskStatus: (id: string, status: CareTask['status'], notes?: string) => void;
  addTask: (task: CareTask) => void;
  removeElder: (elderId: string) => void;
  addElder: (elder: CaregiverElderLink) => void;
}

export const useCaregiverStore = create<CaregiverState>((set, get) => ({
  assignedElders: [],
  selectedElderId: null,
  alerts: [],
  alertHistory: [],
  tasks: [],
  awvRecords: [],
  chronicCare: [],
  elderVitals: {},
  elderMoods: {},
  isLoading: false,

  loadDashboardData: async () => {
    set({ isLoading: true });
    try {
      const alertsResponse = await alertsService.getMyAlerts();
      const rawAlerts = alertsResponse.ok ? alertsResponse.data : [];
      const uniqueElderIds = Array.from(new Set(rawAlerts.map(alert => alert.user_id)));

      const elderResults = await Promise.all(uniqueElderIds.map(async (elderId) => {
        const elderResponse = await healthcareService.getElder(elderId);
        const medicalResponse = await healthcareService.getMedicalProfile(elderId);
        const telemetryResponse = await telemetryService.getLatestTelemetry(elderId, 12);

        const elder = elderResponse.ok ? elderResponse.data : null;
        const telemetry = telemetryResponse.ok ? telemetryResponse.data : [];
        const medicalProfile = medicalResponse.ok ? medicalResponse.data as Record<string, unknown> | null : null;
        const conditions = medicalProfile?.chronic_conditions && typeof medicalProfile.chronic_conditions === 'object'
          ? Object.keys(medicalProfile.chronic_conditions as Record<string, unknown>)
          : [];
        const name = elder?.full_name ?? 'Assigned patient';
        const age = elder?.age ?? 0;
        const latestActivity = telemetry[0]?.recorded_at ?? elder?.created_at ?? new Date().toISOString();

        return {
          elderId,
          link: buildElderRecord(elderId, name, age, conditions, mapSeverityToRisk(rawAlerts.find(alert => alert.user_id === elderId)?.severity ?? 'low'), latestActivity),
          vitals: mapTelemetryToVitals(telemetry),
        };
      }));

      const assignedElders = elderResults.map(result => result.link);
      const elderVitals = elderResults.reduce<Record<string, VitalSign[]>>((acc, result) => {
        acc[result.elderId] = result.vitals;
        return acc;
      }, {});

      const alerts = rawAlerts.map(alert => {
        const matched = elderResults.find(result => result.elderId === alert.user_id);
        return mapBackendAlert(alert, matched?.link.name ?? 'Assigned patient');
      });

      const tasks: CareTask[] = alerts.filter(alert => alert.status === 'active').map((alert, index) => ({
        id: `task-${alert.id}`,
        elderId: assignedElders[index % Math.max(assignedElders.length, 1)]?.elderId ?? alert.id,
        elderName: alert.elderName,
        type: alert.type === 'medication' ? 'medication' : 'follow_up',
        title: `Review ${alert.title}`,
        description: alert.description,
        priority: alert.severity === 'critical' ? 'urgent' : alert.severity === 'high' ? 'high' : 'medium',
        status: 'pending',
        dueDate: new Date(Date.now() + 1000 * 60 * 60 * 6).toISOString(),
        assignedTo: 'Care team',
        notes: alert.recommendedAction,
      }));

      set({
        assignedElders,
        alerts,
        tasks,
        alertHistory: alerts.map(alert => ({
          id: `history-${alert.id}`,
          alertId: alert.id,
          action: alert.status === 'resolved' ? 'Resolved' : 'Fetched from backend',
          performedBy: 'System',
          timestamp: alert.timestamp,
          notes: alert.description,
        })),
        elderVitals,
        chronicCare: [],
        awvRecords: [],
        elderMoods: {},
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  setSelectedElder: (id) => set({ selectedElderId: id }),

  updateAlertStatus: (id, status, notes) =>
    set(s => ({
      alerts: s.alerts.map(a => a.id === id ? { ...a, status } : a),
      alertHistory: [
        { id: `ah-${Date.now()}`, alertId: id, action: `Status changed to ${status}`, performedBy: 'Dr. Smith', timestamp: new Date().toISOString(), notes },
        ...s.alertHistory,
      ],
    })),

  updateTaskStatus: (id, status, notes) =>
    set(s => ({
      tasks: s.tasks.map(t => t.id === id ? { ...t, status, completedAt: status === 'completed' ? new Date().toISOString() : undefined, notes: notes || t.notes } : t),
    })),

  addTask: (task) => set(s => ({ tasks: [task, ...s.tasks] })),

  removeElder: (elderId) =>
    set(s => ({
      assignedElders: s.assignedElders.filter(e => e.elderId !== elderId),
      selectedElderId: s.selectedElderId === elderId ? null : s.selectedElderId,
    })),

  addElder: (elder) =>
    set(s => ({ assignedElders: [...s.assignedElders, elder] })),
}));
