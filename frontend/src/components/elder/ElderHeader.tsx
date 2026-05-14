import React from 'react';
import { useAuthStore } from '@/store/authStore';
import { useElderStore } from '@/store/elderStore';
import { HeartPulse, Star, LogOut, ShieldAlert, Flame } from 'lucide-react';

const ElderHeader: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { wellnessStars, streak, emergency } = useElderStore();

  return (
    <header className="bg-card border-b border-border px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center ring-1 ring-primary/15">
          <HeartPulse className="w-5 h-5 text-primary" strokeWidth={2.25} />
        </div>
        <div className="leading-tight">
          <h1 className="font-heading text-base sm:text-lg font-bold text-foreground tracking-tight">ConnectedCare<span className="text-primary">+</span></h1>
          <p className="text-xs text-muted-foreground">Welcome back, {user?.name?.split(' ')[0] ?? 'friend'}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {emergency.active && (
          <div className="bg-destructive/10 text-destructive px-2.5 py-1 rounded-full text-xs font-semibold animate-pulse flex items-center gap-1.5 ring-1 ring-destructive/20">
            <ShieldAlert className="w-3.5 h-3.5" /> Emergency
          </div>
        )}
        <div className="hidden sm:flex items-center gap-1.5 bg-warning/10 px-2.5 py-1.5 rounded-full ring-1 ring-warning/15">
          <Star className="w-3.5 h-3.5 text-warning fill-warning" />
          <span className="text-xs font-semibold text-foreground">{wellnessStars}</span>
        </div>
        <div className="hidden sm:flex items-center gap-1.5 bg-accent px-2.5 py-1.5 rounded-full">
          <Flame className="w-3.5 h-3.5 text-accent-foreground" />
          <span className="text-xs font-semibold text-accent-foreground">{streak}d</span>
        </div>
        <button
          onClick={logout}
          aria-label="Log out"
          className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center hover:bg-muted/70 transition-colors focus-ring"
        >
          <LogOut className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </header>
  );
};

export default ElderHeader;

