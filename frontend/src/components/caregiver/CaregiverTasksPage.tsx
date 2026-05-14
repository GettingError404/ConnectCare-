'use client';
import React, { useState } from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { CheckCircle, Clock, Play, AlertCircle, Plus, ClipboardList } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CareTask } from '@/types';
import { toast } from 'sonner';

const priorityColor: Record<string, string> = {
  low: 'bg-info/10 text-info',
  medium: 'bg-warning/10 text-warning',
  high: 'bg-high/10 text-high',
  urgent: 'bg-destructive/10 text-destructive',
};

const statusIcon: Record<string, React.ReactNode> = {
  pending: <Clock className="w-4 h-4 text-muted-foreground" />,
  in_progress: <Play className="w-4 h-4 text-primary" />,
  completed: <CheckCircle className="w-4 h-4 text-success" />,
  overdue: <AlertCircle className="w-4 h-4 text-destructive" />,
};

const CaregiverTasksPage: React.FC = () => {
  const { tasks, updateTaskStatus, addTask, assignedElders } = useCaregiverStore();
  const [filter, setFilter] = useState<'active' | 'completed'>('active');

  const activeTasks = tasks.filter(t => t.status !== 'completed').sort((a, b) => {
    const prio = { urgent: 0, high: 1, medium: 2, low: 3 };
    return (prio[a.priority] || 3) - (prio[b.priority] || 3);
  });
  const completedTasks = tasks.filter(t => t.status === 'completed');

  const handleAddTask = () => {
    const newTask: CareTask = {
      id: `ct-${Date.now()}`,
      elderId: assignedElders[0]?.elderId || 'unknown',
      elderName: assignedElders[0]?.name || 'Unknown',
      type: 'check_in',
      title: 'New Check-in Task',
      description: 'Follow up with patient',
      priority: 'medium',
      status: 'pending',
      dueDate: new Date(Date.now() + 86400000).toISOString(),
      assignedTo: 'Dr. Amanda Smith',
    };
    addTask(newTask);
    toast.success('Task added');
  };

  const displayed = filter === 'active' ? activeTasks : completedTasks;

  return (
    <div className="space-y-6 pb-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-foreground">Care Tasks</h2>
          <p className="text-sm text-muted-foreground">{activeTasks.length} active, {completedTasks.length} completed</p>
        </div>
        <Button size="sm" onClick={handleAddTask}>
          <Plus className="w-4 h-4 mr-1" /> New Task
        </Button>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter('active')} className={`px-4 py-1.5 rounded-lg text-xs font-medium ${filter === 'active' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
          Active ({activeTasks.length})
        </button>
        <button onClick={() => setFilter('completed')} className={`px-4 py-1.5 rounded-lg text-xs font-medium ${filter === 'completed' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
          Completed ({completedTasks.length})
        </button>
      </div>

      {displayed.length === 0 && (
        <div className="card-elevated rounded-xl p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-muted text-muted-foreground flex items-center justify-center mx-auto mb-3">
            <ClipboardList className="w-6 h-6" />
          </div>
          <p className="text-sm font-medium text-foreground">No {filter} tasks</p>
          <p className="text-xs text-muted-foreground mt-1">{filter === 'active' ? 'You\'re all caught up' : 'Completed tasks will appear here'}</p>
        </div>
      )}

      <div className="space-y-3">
        {displayed.map(t => (
          <div key={t.id} className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-start gap-3">
              {statusIcon[t.status]}
              <div className="flex-1">
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <h4 className="font-semibold text-foreground text-sm">{t.title}</h4>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${priorityColor[t.priority]}`}>
                    {t.priority.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{t.elderName} · {t.type.replace('_', ' ')}</p>
                <p className="text-xs text-muted-foreground mt-1">{t.description}</p>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Due: {new Date(t.dueDate).toLocaleDateString()} {new Date(t.dueDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>

                {t.status !== 'completed' && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {t.status === 'pending' && (
                      <Button size="sm" variant="outline" onClick={() => { updateTaskStatus(t.id, 'in_progress'); toast('Task started'); }}>
                        <Play className="w-3 h-3 mr-1" /> Start
                      </Button>
                    )}
                    <Button size="sm" variant="outline" onClick={() => { updateTaskStatus(t.id, 'completed'); toast.success('Task completed'); }}>
                      <CheckCircle className="w-3 h-3 mr-1" /> Complete
                    </Button>
                  </div>
                )}
                {t.completedAt && (
                  <p className="text-[10px] text-success mt-1">✓ Completed {new Date(t.completedAt).toLocaleString()}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CaregiverTasksPage;


