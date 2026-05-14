import React from 'react';
import { mockRPMDevices } from '@/data/mockData';
import { Bluetooth, Battery, AlertTriangle, Clock, CheckCircle } from 'lucide-react';

const RPMDevicesPage: React.FC = () => {
  const devices = mockRPMDevices;

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">RPM Devices</h2>
        <p className="text-sm text-muted-foreground">Connected health monitoring devices</p>
      </div>

      <div className="space-y-3">
        {devices.map(d => (
          <div key={d.id} className="bg-card rounded-xl border border-border p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${d.connected ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'}`}>
                  <Bluetooth className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-foreground">{d.name}</p>
                    {d.anomaly && <AlertTriangle className="w-3.5 h-3.5 text-warning" />}
                  </div>
                  <p className="text-xs text-muted-foreground">{d.type}</p>
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-1 justify-end">
                  <Battery className="w-3 h-3 text-muted-foreground" />
                  <span className={`text-xs font-medium ${d.battery < 30 ? 'text-destructive' : d.battery < 60 ? 'text-warning' : 'text-success'}`}>
                    {d.battery}%
                  </span>
                </div>
                <div className="flex items-center gap-1 justify-end mt-1">
                  <Clock className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">
                    {Math.round((Date.now() - new Date(d.lastSync).getTime()) / 60000)}m ago
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RPMDevicesPage;
