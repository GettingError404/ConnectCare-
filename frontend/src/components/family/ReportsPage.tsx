import React from 'react';
import { mockVitalsHistory, mockMoodHistory, mockReminders } from '@/data/mockData';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, BarChart, Bar, Tooltip } from 'recharts';
import { Pill, Droplets, Smile, Activity, AlertTriangle } from 'lucide-react';

const ReportsPage: React.FC = () => {
  const medCompliance = mockReminders.filter(r => r.type === 'medication');
  const taken = medCompliance.filter(r => r.status === 'completed').length;
  const total = medCompliance.length;

  const moodData = mockMoodHistory.slice(0, 7).reverse().map(m => ({
    date: new Date(m.timestamp).toLocaleDateString([], { weekday: 'short' }),
    score: m.score,
  }));

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">Reports & Trends</h2>
        <p className="text-sm text-muted-foreground">Health analytics and adherence summaries</p>
      </div>

      {/* Medication Adherence */}
      <div className="card-elevated rounded-xl p-5">
        <h4 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Pill className="w-4 h-4 text-primary" /> Medication Adherence
        </h4>
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-full border-[6px] border-primary/20 flex items-center justify-center relative shrink-0" style={{ background: `conic-gradient(hsl(var(--primary)) ${total > 0 ? (taken / total) * 360 : 0}deg, hsl(var(--muted)) 0)` }}>
            <div className="w-14 h-14 rounded-full bg-card flex items-center justify-center">
              <span className="font-heading text-base font-bold text-primary">{total > 0 ? Math.round((taken / total) * 100) : 0}%</span>
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">{taken} of {total} medications taken today</p>
            <p className="text-xs text-muted-foreground mt-1">1 missed · {Math.max(total - taken - 1, 0)} upcoming</p>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-3">
        {/* Mood Trend */}
        <div className="card-elevated rounded-xl p-4">
          <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Smile className="w-4 h-4 text-warning" /> Mood Trend (7 days)
          </h4>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={moodData}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} domain={[0, 10]} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 12, fontSize: 12 }} />
              <Line type="monotone" dataKey="score" stroke="hsl(var(--warning))" strokeWidth={2} dot={{ fill: 'hsl(var(--warning))', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* BP Trend */}
        <div className="card-elevated rounded-xl p-4">
          <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-destructive" /> Blood Pressure (Weekly)
          </h4>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={mockVitalsHistory.blood_pressure_sys}>
              <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} domain={[100, 160]} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 12, fontSize: 12 }} />
              <Bar dataKey="value" fill="hsl(var(--destructive))" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Glucose Trend */}
        <div className="card-elevated rounded-xl p-4 lg:col-span-2">
          <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Droplets className="w-4 h-4 text-info" /> Glucose (Weekly)
          </h4>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={mockVitalsHistory.glucose}>
              <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} domain={[80, 180]} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 12, fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="hsl(var(--info))" strokeWidth={2} dot={{ fill: 'hsl(var(--info))', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default ReportsPage;
