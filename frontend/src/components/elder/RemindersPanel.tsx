import React from 'react';
import { useElderStore } from '@/store/elderStore';
import { Pill, Droplets, Calendar, Footprints, Check, Clock, X, RotateCcw } from 'lucide-react';
import { Reminder } from '@/types';

const iconMap: Record<string, React.ReactNode> = {
  medication: <Pill className="w-5 h-5" />,
  hydration: <Droplets className="w-5 h-5" />,
  appointment: <Calendar className="w-5 h-5" />,
  movement: <Footprints className="w-5 h-5" />,
};

const statusColors: Record<string, string> = {
  upcoming: 'bg-info/10 text-info',
  completed: 'bg-success/10 text-success',
  missed: 'bg-destructive/10 text-destructive',
  snoozed: 'bg-warning/10 text-warning',
};

const ReminderCard: React.FC<{ reminder: Reminder; onAction: (id: string, status: Reminder['status']) => void }> = ({ reminder, onAction }) => (
  <div className="bg-card rounded-xl border border-border p-4 flex items-center gap-3 shadow-sm">
    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${statusColors[reminder.status]}`}>
      {iconMap[reminder.type]}
    </div>
    <div className="flex-1 min-w-0">
      <p className="font-medium text-foreground text-base truncate">{reminder.title}</p>
      <p className="text-sm text-muted-foreground">{reminder.description}</p>
      <p className="text-xs text-muted-foreground mt-0.5">
        {new Date(reminder.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </p>
    </div>
    {reminder.status === 'upcoming' && (
      <div className="flex gap-1">
        <button onClick={() => onAction(reminder.id, 'completed')} className="w-9 h-9 rounded-lg bg-success/10 text-success flex items-center justify-center hover:bg-success/20 transition-colors">
          <Check className="w-4 h-4" />
        </button>
        <button onClick={() => onAction(reminder.id, 'snoozed')} className="w-9 h-9 rounded-lg bg-warning/10 text-warning flex items-center justify-center hover:bg-warning/20 transition-colors">
          <Clock className="w-4 h-4" />
        </button>
      </div>
    )}
    {reminder.status === 'missed' && (
      <button onClick={() => onAction(reminder.id, 'completed')} className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center hover:bg-muted/80 transition-colors">
        <RotateCcw className="w-4 h-4 text-muted-foreground" />
      </button>
    )}
    {reminder.status === 'completed' && (
      <div className="w-8 h-8 rounded-full bg-success/10 flex items-center justify-center">
        <Check className="w-4 h-4 text-success" />
      </div>
    )}
  </div>
);

const RemindersPanel: React.FC = () => {
  const { reminders, updateReminderStatus, addStars } = useElderStore();

  const handleAction = (id: string, status: Reminder['status']) => {
    updateReminderStatus(id, status);
    if (status === 'completed') addStars(5, 'Reminder completed');
  };

  const upcoming = reminders.filter(r => r.status === 'upcoming');
  const completed = reminders.filter(r => r.status === 'completed');
  const missed = reminders.filter(r => r.status === 'missed');

  return (
    <div className="space-y-5 max-w-2xl mx-auto">
      <div>
        <h3 className="font-heading text-xl font-semibold text-foreground tracking-tight">Today's Reminders</h3>
        <p className="text-sm text-muted-foreground mt-0.5">Stay on track with your care plan</p>
      </div>

      {missed.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-destructive">Missed ({missed.length})</p>
          {missed.map(r => <ReminderCard key={r.id} reminder={r} onAction={handleAction} />)}
        </div>
      )}

      {upcoming.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-info">Upcoming ({upcoming.length})</p>
          {upcoming.map(r => <ReminderCard key={r.id} reminder={r} onAction={handleAction} />)}
        </div>
      )}

      {completed.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-success">Completed ({completed.length})</p>
          {completed.map(r => <ReminderCard key={r.id} reminder={r} onAction={handleAction} />)}
        </div>
      )}
    </div>
  );
};

export default RemindersPanel;

