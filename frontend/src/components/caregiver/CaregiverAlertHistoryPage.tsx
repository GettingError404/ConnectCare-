import React from 'react';
import { useCaregiverStore } from '@/store/caregiverStore';
import { History, User, FileText } from 'lucide-react';

const CaregiverAlertHistoryPage: React.FC = () => {
  const { alertHistory } = useCaregiverStore();

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground">Alert History</h2>
        <p className="text-sm text-muted-foreground">Complete log of all alert actions and responses</p>
      </div>

      <div className="relative">
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-border" />
        <div className="space-y-4">
          {alertHistory.map(entry => (
            <div key={entry.id} className="flex gap-4 relative">
              <div className="w-10 h-10 rounded-full bg-card border-2 border-border flex items-center justify-center z-10 shrink-0">
                <History className="w-4 h-4 text-muted-foreground" />
              </div>
              <div className="bg-card rounded-xl border border-border p-4 flex-1">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-semibold text-foreground text-sm">{entry.action}</h4>
                  <span className="text-[10px] text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <User className="w-3 h-3" /> {entry.performedBy}
                </div>
                {entry.notes && (
                  <div className="flex items-start gap-1 text-xs text-muted-foreground mt-1">
                    <FileText className="w-3 h-3 mt-0.5 shrink-0" />
                    <span>{entry.notes}</span>
                  </div>
                )}
                <p className="text-[10px] text-muted-foreground mt-1">Alert ID: {entry.alertId}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CaregiverAlertHistoryPage;

