import React from 'react';
import { Settings, User, Bell, Shield } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';

const SettingsPage: React.FC = () => {
  const { user, logout } = useAuthStore();

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">Settings</h2>
        <p className="text-sm text-muted-foreground">Account and notification preferences</p>
      </div>

      <div className="card-elevated rounded-xl p-5">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-lg">
            {user?.name?.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase() ?? 'U'}
          </div>
          <div className="min-w-0">
            <p className="font-heading font-bold text-foreground truncate">{user?.name}</p>
            <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
            <p className="text-xs text-primary font-medium capitalize mt-0.5">{user?.role} member</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {[
          { icon: <User className="w-4 h-4" />, label: 'Profile Settings', desc: 'Update name, contact info' },
          { icon: <Bell className="w-4 h-4" />, label: 'Notification Preferences', desc: 'Alert thresholds, channels' },
          { icon: <Shield className="w-4 h-4" />, label: 'Privacy & Security', desc: 'Password, data sharing' },
        ].map((item, i) => (
          <div key={i} className="bg-card rounded-xl border border-border p-4 shadow-sm flex items-center gap-3 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">{item.icon}</div>
            <div>
              <p className="text-sm font-medium text-foreground">{item.label}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <Button variant="outline" className="w-full" onClick={logout}>Sign Out</Button>
    </div>
  );
};

export default SettingsPage;

