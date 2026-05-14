import { create } from 'zustand';
import { Alert, ActivityEvent } from '@/types';
import { alertsService, type BackendAlert } from '@/lib/api/services/alerts';

function mapBackendAlert(alert: BackendAlert): Alert {
  const type = alert.alert_type.includes('vital') || alert.alert_type.includes('bp') || alert.alert_type.includes('glucose')
    ? 'vitals'
    : alert.alert_type.includes('med')
      ? 'medication'
      : alert.alert_type.includes('mood')
        ? 'mood'
        : alert.alert_type.includes('fall')
          ? 'fall'
          : alert.alert_type.includes('check')
            ? 'checkin'
            : 'cognitive';

  return {
    id: alert.id,
    type,
    severity: alert.severity as Alert['severity'],
    title: alert.alert_type.replace(/_/g, ' '),
    description: alert.message,
    timestamp: alert.created_at,
    status: alert.is_resolved ? 'resolved' : 'active',
    elderName: 'Assigned elder',
    recommendedAction: alert.is_resolved ? 'No action required' : 'Review alert details',
  };
}

function buildActivityTimeline(alerts: Alert[]): ActivityEvent[] {
  return alerts.slice(0, 10).map((alert, index) => ({
    id: `timeline-${alert.id}`,
    type: `alert-${index}`,
    title: alert.title,
    description: alert.description,
    timestamp: alert.timestamp,
    category: 'alert',
  }));
}

interface FamilyState {
  alerts: Alert[];
  activityTimeline: ActivityEvent[];
  selectedElderId: string;
  isLoading: boolean;
  
  loadDashboardData: () => Promise<void>;
  setSelectedElder: (id: string) => void;
  updateAlertStatus: (id: string, status: Alert['status']) => void;
  addAlert: (alert: Alert) => void;
}

export const useFamilyStore = create<FamilyState>((set) => ({
  alerts: [],
  activityTimeline: [],
  selectedElderId: '',
  isLoading: false,

  loadDashboardData: async () => {
    set({ isLoading: true });
    try {
      const response = await alertsService.getMyAlerts();
      const alerts = response.ok ? response.data.map(mapBackendAlert) : [];
      set({ alerts, activityTimeline: buildActivityTimeline(alerts), isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  setSelectedElder: (id) => set({ selectedElderId: id }),
  updateAlertStatus: (id, status) =>
    set(s => ({ alerts: s.alerts.map(a => a.id === id ? { ...a, status } : a) })),
  addAlert: (alert) =>
    set(s => ({ alerts: [alert, ...s.alerts] })),
}));
