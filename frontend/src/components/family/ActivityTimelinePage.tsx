import React from 'react';
import { mockActivityTimeline } from '@/data/mockData';
import { Pill, Droplets, Smile, ClipboardCheck, Dumbbell, Sparkles, Home, AlertTriangle, Shield, Activity } from 'lucide-react';

const categoryIcons: Record<string, React.ReactNode> = {
  medication: <Pill className="w-4 h-4" />,
  hydration: <Droplets className="w-4 h-4" />,
  mood: <Smile className="w-4 h-4" />,
  checkin: <ClipboardCheck className="w-4 h-4" />,
  exercise: <Dumbbell className="w-4 h-4" />,
  intervention: <Sparkles className="w-4 h-4" />,
  smart_home: <Home className="w-4 h-4" />,
  alert: <AlertTriangle className="w-4 h-4" />,
  emergency: <Shield className="w-4 h-4" />,
  vitals: <Activity className="w-4 h-4" />,
};

const categoryColors: Record<string, string> = {
  medication: 'bg-primary/10 text-primary border-primary/20',
  hydration: 'bg-info/10 text-info border-info/20',
  mood: 'bg-warning/10 text-warning border-warning/20',
  checkin: 'bg-success/10 text-success border-success/20',
  exercise: 'bg-primary/10 text-primary border-primary/20',
  intervention: 'bg-accent text-accent-foreground border-accent/20',
  smart_home: 'bg-muted text-muted-foreground border-border',
  alert: 'bg-destructive/10 text-destructive border-destructive/20',
  emergency: 'bg-destructive/10 text-destructive border-destructive/20',
  vitals: 'bg-success/10 text-success border-success/20',
};

const ActivityTimelinePage: React.FC = () => {
  const timeline = mockActivityTimeline;

  return (
    <div className="space-y-4 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">Activity Timeline</h2>
        <p className="text-sm text-muted-foreground">Chronological activity log for Margaret</p>
      </div>

      <div className="relative">
        <div className="absolute left-5 top-0 bottom-0 w-px bg-border" />
        <div className="space-y-4">
          {timeline.map(event => (
            <div key={event.id} className="flex items-start gap-3 pl-2">
              <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center shrink-0 z-10 ${categoryColors[event.category]}`}>
                {categoryIcons[event.category]}
              </div>
              <div className="bg-card rounded-xl border border-border px-4 py-3 flex-1 shadow-sm">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-foreground">{event.title}</h4>
                  <span className="text-[10px] text-muted-foreground">{new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{event.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ActivityTimelinePage;
