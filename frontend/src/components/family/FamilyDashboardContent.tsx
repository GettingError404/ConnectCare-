import React, { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useFamilyStore } from '@/store/familyStore';
import { useElderStore } from '@/store/elderStore';
import {
  Heart, Activity, Droplets, Footprints, AlertTriangle, TrendingUp,
  Clock, Shield, Bell, Pill, Brain, Smile, Thermometer,
  CheckCircle, XCircle, Eye, ChevronRight, Phone
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, BarChart, Bar, Tooltip } from 'recharts';

const severityColor: Record<string, string> = {
  low: 'bg-info/10 text-info border-info/20',
  medium: 'bg-warning/10 text-warning border-warning/20',
  high: 'bg-high/10 text-high border-high/20',
  critical: 'bg-destructive/10 text-destructive border-destructive/20',
};

const FamilyDashboardContent: React.FC = () => {
  const { user } = useAuthStore();
  const { alerts, loadDashboardData } = useFamilyStore();
  const {
    loadDashboardData: loadElderDashboardData,
    vitals,
    moodHistory,
    vitalsHistory,
    profile,
    wellnessStars,
    streak,
  } = useElderStore();
  const activeAlerts = alerts.filter(a => a.status === 'active' || a.status === 'escalated');

  useEffect(() => {
    void loadDashboardData();
    if (user?.role === 'elder' || user?.role === 'admin') {
      void loadElderDashboardData();
    }
  }, [loadDashboardData, loadElderDashboardData, user?.role]);

  const elderName = profile?.name ?? 'Margaret Johnson';
  const elderInitials = elderName.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
  const elderSummary = profile ? profile.email : '78 yrs · Hypertension, Type 2 Diabetes';

  // AI Insights
  const insights = [
    { icon: <Pill className="w-4 h-4" />, text: 'Evening vitamins missed yesterday', severity: 'high' as const },
    { icon: <TrendingUp className="w-4 h-4" />, text: 'Blood pressure trending up this week', severity: 'medium' as const },
    { icon: <Smile className="w-4 h-4" />, text: 'Two low mood entries detected this week', severity: 'medium' as const },
    { icon: <Footprints className="w-4 h-4" />, text: 'Activity below daily goal today', severity: 'low' as const },
    { icon: <Droplets className="w-4 h-4" />, text: 'Glucose at 142 mg/dL — above target', severity: 'medium' as const },
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* Elder Summary */}
      <div className="card-elevated rounded-2xl p-5">
        <div className="flex items-start sm:items-center justify-between gap-3 mb-4 flex-wrap">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-base shrink-0">{elderInitials}</div>
            <div className="min-w-0">
              <h2 className="font-heading text-lg font-bold text-foreground truncate">{elderName}</h2>
              <p className="text-xs sm:text-sm text-muted-foreground truncate">{elderSummary}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-success/10">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            <span className="text-xs text-success font-semibold">Online</span>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="bg-success/5 border border-success/15 rounded-xl p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">Risk</p>
            <p className="font-heading font-bold text-success mt-0.5">Low</p>
          </div>
          <div className="bg-warning/5 border border-warning/15 rounded-xl p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">Alerts</p>
            <p className="font-heading font-bold text-warning mt-0.5">{activeAlerts.length}</p>
          </div>
          <div className="bg-primary/5 border border-primary/15 rounded-xl p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">Wellness</p>
            <p className="font-heading font-bold text-primary mt-0.5">{wellnessStars} ★</p>
          </div>
          <div className="bg-info/5 border border-info/15 rounded-xl p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">Streak</p>
            <p className="font-heading font-bold text-info mt-0.5">{streak} d</p>
          </div>
        </div>
      </div>

      {/* AI Insights */}
      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" /> AI-Driven Insights
        </h3>
        <div className="space-y-2">
          {insights.map((insight, i) => (
            <div key={i} className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${severityColor[insight.severity]}`}>
              {insight.icon}
              <span className="text-sm font-medium">{insight.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Vitals Grid */}
      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3">Physical Health</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {vitals.map(v => (
            <div key={v.id} className="bg-card rounded-xl border border-border p-4 shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">{v.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                  v.status === 'normal' ? 'bg-success/10 text-success' : v.status === 'warning' ? 'bg-warning/10 text-warning' : 'bg-destructive/10 text-destructive'
                }`}>{v.status}</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{v.value}<span className="text-xs font-normal text-muted-foreground ml-1">{v.unit}</span></p>
              <div className="flex items-center gap-1 mt-1">
                <TrendingUp className={`w-3 h-3 ${v.trend === 'up' ? 'text-warning' : v.trend === 'down' ? 'text-info' : 'text-muted-foreground'}`} />
                <span className="text-[10px] text-muted-foreground">{v.trend}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Charts grid */}
      <div className="grid lg:grid-cols-2 gap-3">
        <div className="card-elevated rounded-xl p-4">
          <h4 className="text-sm font-semibold text-foreground mb-3">Heart Rate (24h)</h4>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={vitalsHistory.heart_rate}>
              <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} domain={[60, 90]} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 12, fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card-elevated rounded-xl p-4">
          <h4 className="text-sm font-semibold text-foreground mb-3">Weekly Activity (Steps)</h4>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={vitalsHistory.activity}>
              <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 12, fontSize: 12 }} />
              <Bar dataKey="value" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Mood Trends */}
      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3">Emotional Wellness</h3>
        <div className="space-y-2">
          {moodHistory.slice(0, 5).map(m => (
            <div key={m.id} className="bg-card rounded-xl border border-border px-4 py-3 flex items-center gap-3 shadow-sm">
              <span className="text-xl">
                {m.mood === 'happy' ? '😊' : m.mood === 'calm' ? '😌' : m.mood === 'sad' ? '😢' : m.mood === 'lonely' ? '😔' : m.mood === 'anxious' ? '😰' : '😐'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground capitalize">{m.mood}</p>
                <p className="text-xs text-muted-foreground truncate">{m.note}</p>
              </div>
              <div className="text-right">
                <p className={`text-xs font-medium ${m.sentiment === 'positive' ? 'text-success' : m.sentiment === 'negative' ? 'text-warning' : m.sentiment === 'risk' ? 'text-destructive' : 'text-muted-foreground'}`}>
                  {m.score}/10
                </p>
                <p className="text-[10px] text-muted-foreground">{new Date(m.timestamp).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Alerts */}
      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <Bell className="w-4 h-4 text-warning" /> Recent Alerts
        </h3>
        <div className="space-y-2">
          {alerts.slice(0, 4).map(a => (
            <div key={a.id} className={`rounded-xl border px-4 py-3 ${severityColor[a.severity]}`}>
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">{a.title}</p>
                <span className="text-[10px] font-medium uppercase">{a.severity}</span>
              </div>
              <p className="text-xs mt-1 opacity-80">{a.description}</p>
              <p className="text-[10px] mt-1 opacity-60">{new Date(a.timestamp).toLocaleString()}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FamilyDashboardContent;

