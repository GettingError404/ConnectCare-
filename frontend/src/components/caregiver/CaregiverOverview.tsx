import React from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { Users, AlertTriangle, ClipboardList, Activity, TrendingUp, TrendingDown, Minus, ShieldAlert } from 'lucide-react';

interface Props {
  onNavigate: (page: 'overview' | 'patients' | 'alerts' | 'tasks' | 'vitals' | 'awv' | 'chronic' | 'alert_history' | 'telehealth') => void;
}

const CaregiverOverview: React.FC<Props> = ({ onNavigate }) => {
  const { assignedElders, alerts, tasks, chronicCare } = useCaregiverStore();

  const activeAlerts = alerts.filter(a => a.status === 'active').length;
  const criticalAlerts = alerts.filter(a => a.severity === 'critical' && a.status === 'active').length;
  const pendingTasks = tasks.filter(t => t.status === 'pending' || t.status === 'in_progress').length;
  const urgentTasks = tasks.filter(t => t.priority === 'urgent' && t.status !== 'completed').length;
  const highRiskPatients = assignedElders.filter(e => e.riskLevel === 'high' || e.riskLevel === 'critical').length;
  const nonCompliant = chronicCare.filter(c => c.status === 'non_compliant').length;

  const stats = [
    { label: 'Total Patients', value: assignedElders.length, icon: Users, color: 'text-primary', bg: 'bg-primary/10', onClick: () => onNavigate('patients') },
    { label: 'Active Alerts', value: activeAlerts, sub: `${criticalAlerts} critical`, icon: AlertTriangle, color: 'text-destructive', bg: 'bg-destructive/10', onClick: () => onNavigate('alerts') },
    { label: 'Pending Tasks', value: pendingTasks, sub: `${urgentTasks} urgent`, icon: ClipboardList, color: 'text-warning', bg: 'bg-warning/10', onClick: () => onNavigate('tasks') },
    { label: 'High Risk', value: highRiskPatients, sub: `${nonCompliant} non-compliant`, icon: ShieldAlert, color: 'text-high', bg: 'bg-high/5', onClick: () => onNavigate('chronic') },
  ];

  const trendIcon = (t: string) => t === 'improving' ? <TrendingUp className="w-3.5 h-3.5 text-success" /> : t === 'declining' ? <TrendingDown className="w-3.5 h-3.5 text-destructive" /> : <Minus className="w-3.5 h-3.5 text-muted-foreground" />;

  const riskColor: Record<string, string> = {
    low: 'bg-success/10 text-success',
    moderate: 'bg-warning/10 text-warning',
    high: 'bg-high/10 text-high',
    critical: 'bg-destructive/10 text-destructive',
  };

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Good Morning, Dr. Smith</h2>
        <p className="text-sm text-muted-foreground">You have {activeAlerts} active alerts and {pendingTasks} pending tasks</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map(s => (
          <button key={s.label} onClick={s.onClick} className="bg-card rounded-xl border border-border p-4 text-left hover:shadow-md transition-shadow">
            <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center mb-3`}>
              <s.icon className={`w-5 h-5 ${s.color}`} />
            </div>
            <p className="text-2xl font-bold text-foreground">{s.value}</p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
            {s.sub && <p className="text-[10px] text-muted-foreground mt-0.5">{s.sub}</p>}
          </button>
        ))}
      </div>

      {/* Critical Alerts */}
      {criticalAlerts > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-destructive flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Critical Alerts
          </h3>
          {alerts.filter(a => a.severity === 'critical' && a.status === 'active').map(a => (
            <div key={a.id} className="bg-destructive/5 border-2 border-destructive/30 rounded-xl p-4">
              <h4 className="font-semibold text-foreground text-sm">{a.title}</h4>
              <p className="text-xs text-muted-foreground mt-1">{a.description}</p>
              <p className="text-xs text-destructive mt-2 font-medium">⚡ {a.recommendedAction}</p>
            </div>
          ))}
        </div>
      )}

      {/* Patient Quick View */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Patient Overview</h3>
          <button onClick={() => onNavigate('patients')} className="text-xs text-primary hover:underline">View All →</button>
        </div>
        <div className="space-y-2">
          {assignedElders.map(e => {
            const init = e.name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
            return (
              <div key={e.elderId} className="card-elevated rounded-xl p-4 flex items-center gap-4">
                <div className="relative shrink-0">
                  <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-sm">
                    {init}
                  </div>
                  <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-card ${e.status === 'online' ? 'bg-success' : 'bg-muted-foreground'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-foreground text-sm truncate">{e.name}</p>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${riskColor[e.riskLevel]}`}>
                      {e.riskLevel.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate">{e.conditions.slice(0, 2).join(', ')}</p>
                </div>
                <div className="hidden sm:flex items-center gap-4 text-xs">
                  <div className="text-center">
                    <p className="text-muted-foreground">Meds</p>
                    <p className={`font-bold ${e.medicationAdherence < 60 ? 'text-destructive' : e.medicationAdherence < 80 ? 'text-warning' : 'text-success'}`}>{e.medicationAdherence}%</p>
                  </div>
                  <div className="text-center">
                    <p className="text-muted-foreground">Mood</p>
                    <div className="flex justify-center">{trendIcon(e.moodTrend)}</div>
                  </div>
                  <div className="text-center">
                    <p className="text-muted-foreground">Cognitive</p>
                    <p className={`font-bold ${e.cognitiveScore < 50 ? 'text-destructive' : e.cognitiveScore < 70 ? 'text-warning' : 'text-foreground'}`}>{e.cognitiveScore}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CaregiverOverview;

