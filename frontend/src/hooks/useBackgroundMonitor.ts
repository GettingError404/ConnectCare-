import { useEffect, useRef, useCallback } from 'react';
import { useElderStore } from '@/store/elderStore';

interface UseBackgroundMonitorOptions {
  onProactiveSpeak: (message: string) => void;
  enabled: boolean;
}

export function useBackgroundMonitor({ onProactiveSpeak, enabled }: UseBackgroundMonitorOptions) {
  const store = useElderStore();
  const spokenRemindersRef = useRef<Set<string>>(new Set());
  const lastInactivityCheckRef = useRef(Date.now());
  const lastVitalsAlertRef = useRef(0);

  // Check for due reminders every 15 seconds
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      const now = new Date();
      const { reminders } = useElderStore.getState();

      reminders.forEach(r => {
        if (r.status !== 'upcoming') return;
        if (spokenRemindersRef.current.has(r.id)) return;

        const reminderTime = new Date(r.time);
        const diffMs = reminderTime.getTime() - now.getTime();
        const diffMin = diffMs / 60000;

        // Trigger if reminder is due (within 2 minutes) or overdue
        if (diffMin <= 2 && diffMin > -10) {
          spokenRemindersRef.current.add(r.id);
          const typeLabel = r.type === 'medication' ? '💊' : r.type === 'hydration' ? '💧' : r.type === 'movement' ? '🚶' : '📅';
          onProactiveSpeak(`${typeLabel} Reminder: ${r.title}. ${r.description}. Would you like to mark it as done, or should I remind you later?`);
        }
      });
    }, 15000);

    return () => clearInterval(interval);
  }, [enabled, onProactiveSpeak]);

  // Check for abnormal vitals every 60 seconds
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      const { vitals } = useElderStore.getState();
      const now = Date.now();

      // Don't alert more than once per 5 minutes
      if (now - lastVitalsAlertRef.current < 300000) return;

      const critical = vitals.filter(v => v.status === 'critical');
      if (critical.length > 0) {
        lastVitalsAlertRef.current = now;
        const labels = critical.map(v => {
          const names: Record<string, string> = {
            heart_rate: 'heart rate', blood_pressure: 'blood pressure',
            glucose: 'glucose', spo2: 'oxygen level', temperature: 'temperature',
          };
          return `${names[v.type] || v.type} at ${v.value} ${v.unit}`;
        }).join(', ');
        onProactiveSpeak(`⚠️ Health alert: Your ${labels} is outside the safe range. I'm noting this for your family. Would you like me to contact someone?`);
      }
    }, 60000);

    return () => clearInterval(interval);
  }, [enabled, onProactiveSpeak]);

  // Periodic wellness check-in (every 2 hours of inactivity from the user)
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const { chatMessages } = useElderStore.getState();
      const lastUserMsg = chatMessages.filter(m => m.role === 'user').pop();
      const lastUserTime = lastUserMsg ? new Date(lastUserMsg.timestamp).getTime() : 0;
      const inactiveMinutes = (now - lastUserTime) / 60000;

      if (inactiveMinutes > 120 && now - lastInactivityCheckRef.current > 7200000) {
        lastInactivityCheckRef.current = now;
        onProactiveSpeak(`Hi! I noticed it's been a while since we talked. Are you doing okay? Would you like to do a quick check-in or maybe stretch a little?`);
      }
    }, 300000); // Check every 5 min

    return () => clearInterval(interval);
  }, [enabled, onProactiveSpeak]);
}

