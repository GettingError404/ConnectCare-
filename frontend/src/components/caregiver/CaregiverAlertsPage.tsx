'use client';
import React, { useState } from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { AlertTriangle, CheckCircle, Eye, ArrowUpRight, Clock, Filter, BellOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const severityColor: Record<string, string> = {
  low: 'border-info/30 bg-info/5',
  medium: 'border-warning/30 bg-warning/5',
  high: 'border-high/30 bg-high/5',
  critical: 'border-destructive/30 bg-destructive/5',
};

const severityDot: Record<string, string> = {
  low: 'bg-info',
  medium: 'bg-warning',
  high: 'bg-high',
  critical: 'bg-destructive',
};

const CaregiverAlertsPage: React.FC = () => {
  const { alerts, updateAlertStatus } = useCaregiverStore();
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  const active = alerts.filter(a => (a.status === 'active' || a.status === 'escalated') && (filter === 'all' || a.severity === filter));
  const resolved = alerts.filter(a => a.status === 'acknowledged' || a.status === 'resolved');

  const filterBtns: { id: typeof filter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'critical', label: 'Critical' },
    { id: 'high', label: 'High' },
    { id: 'medium', label: 'Medium' },
    { id: 'low', label: 'Low' },
  ];

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Alert Management</h2>
        <p className="text-sm text-muted-foreground">{active.length} active alerts across all patients</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {filterBtns.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === f.id ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Active Alerts</h3>
        {active.map(a => (
          <div key={a.id} className={`rounded-xl border-2 p-4 ${severityColor[a.severity]}`}>
            <div className="flex items-start gap-3">
              <div className={`w-2.5 h-2.5 rounded-full mt-1.5 ${severityDot[a.severity]}`} />
              <div className="flex-1">
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <h4 className="font-semibold text-foreground text-sm">{a.title}</h4>
                  <span className="text-[10px] font-bold uppercase text-muted-foreground">{a.severity}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{a.description}</p>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {new Date(a.timestamp).toLocaleString()}
                </p>
                <div className="bg-muted/50 rounded-lg p-2 mt-2">
                  <p className="text-xs text-muted-foreground"><strong>Recommended:</strong> {a.recommendedAction}</p>
                </div>
                <div className="flex gap-2 mt-3 flex-wrap">
                  <Button size="sm" variant="outline" onClick={() => { updateAlertStatus(a.id, 'acknowledged', 'Acknowledged by caregiver'); toast.success('Acknowledged'); }}>
                    <Eye className="w-3 h-3 mr-1" /> Acknowledge
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => { updateAlertStatus(a.id, 'resolved', 'Resolved by caregiver'); toast.success('Resolved'); }}>
                    <CheckCircle className="w-3 h-3 mr-1" /> Resolve
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => { updateAlertStatus(a.id, 'escalated', 'Escalated to specialist'); toast('Escalated to specialist'); }}>
                    <ArrowUpRight className="w-3 h-3 mr-1" /> Escalate
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ))}
        {active.length === 0 && (
          <div className="card-elevated rounded-xl p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-success/10 text-success flex items-center justify-center mx-auto mb-3">
              <BellOff className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-foreground">No alerts matching filter</p>
            <p className="text-xs text-muted-foreground mt-1">Try a different filter or check back later</p>
          </div>
        )}
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Resolved / Acknowledged</h3>
        {resolved.map(a => (
          <div key={a.id} className="rounded-xl border border-border bg-card p-4 opacity-70">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-foreground">{a.title}</h4>
              <span className="text-[10px] font-medium text-success uppercase">{a.status}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">{a.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CaregiverAlertsPage;


