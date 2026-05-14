'use client';
import React, { useState } from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { UserPlus, UserMinus, TrendingUp, TrendingDown, Minus, Search, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CaregiverElderLink } from '@/types';
import { toast } from 'sonner';

const CaregiverPatientsPage: React.FC = () => {
  const { assignedElders, removeElder, addElder, selectedElderId, setSelectedElder } = useCaregiverStore();
  const [search, setSearch] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);

  const filtered = assignedElders.filter(e => e.name.toLowerCase().includes(search.toLowerCase()));

  const trendIcon = (t: string) => t === 'improving' ? <TrendingUp className="w-4 h-4 text-success" /> : t === 'declining' ? <TrendingDown className="w-4 h-4 text-destructive" /> : <Minus className="w-4 h-4 text-muted-foreground" />;

  const riskBorder: Record<string, string> = {
    low: 'border-l-success',
    moderate: 'border-l-warning',
    high: 'border-l-high',
    critical: 'border-l-destructive',
  };

  const handleAddSample = () => {
    const sample: CaregiverElderLink = {
      elderId: `elder-${Date.now()}`,
      name: 'New Patient',
      age: 75,
      conditions: ['To be assessed'],
      riskLevel: 'low',
      status: 'offline',
      lastActive: new Date().toISOString(),
      medicationAdherence: 0,
      moodTrend: 'stable',
      lastCheckIn: new Date().toISOString(),
      cognitiveScore: 0,
    };
    addElder(sample);
    setShowAddDialog(false);
    toast.success('Patient added to your caseload');
  };

  const handleRemove = (id: string, name: string) => {
    removeElder(id);
    toast(`Removed ${name}`, { description: 'Patient unassigned' });
  };

  return (
    <div className="space-y-6 pb-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-foreground">Patient Management</h2>
          <p className="text-sm text-muted-foreground">{assignedElders.length} assigned patients</p>
        </div>
        <Button size="sm" onClick={handleAddSample}>
          <UserPlus className="w-4 h-4 mr-1" /> Add Patient
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input placeholder="Search patients..." value={search} onChange={e => setSearch(e.target.value)} className="pl-10" />
      </div>

      {filtered.length === 0 && (
        <div className="card-elevated rounded-xl p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-muted text-muted-foreground flex items-center justify-center mx-auto mb-3">
            <Users className="w-6 h-6" />
          </div>
          <p className="text-sm font-medium text-foreground">No patients found</p>
          <p className="text-xs text-muted-foreground mt-1">{search ? 'Try a different search term' : 'Add your first patient to get started'}</p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        {filtered.map(e => (
          <div
            key={e.elderId}
            className={`bg-card rounded-xl border border-border border-l-4 ${riskBorder[e.riskLevel]} p-5 cursor-pointer hover:shadow-md transition-shadow ${selectedElderId === e.elderId ? 'ring-2 ring-primary' : ''}`}
            onClick={() => setSelectedElder(e.elderId)}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-foreground">{e.name}</h3>
                  <span className={`w-2 h-2 rounded-full ${e.status === 'online' ? 'bg-success' : 'bg-muted-foreground'}`} />
                </div>
                <p className="text-xs text-muted-foreground">Age {e.age} · {e.conditions.join(', ')}</p>
              </div>
              <Button size="sm" variant="ghost" aria-label={`Remove ${e.name}`} onClick={(ev) => { ev.stopPropagation(); handleRemove(e.elderId, e.name); }}>
                <UserMinus className="w-4 h-4 text-destructive" />
              </Button>
            </div>

            <div className="grid grid-cols-4 gap-3">
              <div className="bg-muted/50 rounded-lg p-2 text-center">
                <p className="text-[10px] text-muted-foreground">Med Adherence</p>
                <p className={`text-lg font-bold ${e.medicationAdherence < 60 ? 'text-destructive' : e.medicationAdherence < 80 ? 'text-warning' : 'text-success'}`}>{e.medicationAdherence}%</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-2 text-center">
                <p className="text-[10px] text-muted-foreground">Mood Trend</p>
                <div className="flex justify-center mt-1">{trendIcon(e.moodTrend)}</div>
                <p className="text-[10px] capitalize text-muted-foreground">{e.moodTrend}</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-2 text-center">
                <p className="text-[10px] text-muted-foreground">Cognitive</p>
                <p className={`text-lg font-bold ${e.cognitiveScore < 50 ? 'text-destructive' : e.cognitiveScore < 70 ? 'text-warning' : 'text-foreground'}`}>{e.cognitiveScore}</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-2 text-center">
                <p className="text-[10px] text-muted-foreground">Risk Level</p>
                <p className={`text-sm font-bold capitalize ${e.riskLevel === 'critical' ? 'text-destructive' : e.riskLevel === 'high' ? 'text-high' : e.riskLevel === 'moderate' ? 'text-warning' : 'text-success'}`}>{e.riskLevel}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CaregiverPatientsPage;


