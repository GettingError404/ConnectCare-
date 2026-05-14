'use client';
import React, { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { FamilyProfile } from '@/types';
import {
  LayoutDashboard, AlertTriangle, BarChart3, Activity, MessageCircle,
  Phone, Home, Settings, Heart, LogOut, Bell, ChevronDown, Menu, X
} from 'lucide-react';
import FamilyDashboardContent from '@/components/family/FamilyDashboardContent';
import AlertsPage from '@/components/family/AlertsPage';
import ChatVisibilityPage from '@/components/family/ChatVisibilityPage';
import ActivityTimelinePage from '@/components/family/ActivityTimelinePage';
import EmergencyTelehealthPage from '@/components/family/EmergencyTelehealthPage';
import SmartHomeFamilyPage from '@/components/family/SmartHomeFamilyPage';
import RPMDevicesPage from '@/components/family/RPMDevicesPage';
import ReportsPage from '@/components/family/ReportsPage';
import SettingsPage from '@/components/family/SettingsPage';
import { useFamilyStore } from '@/store/familyStore';

type Page = 'dashboard' | 'alerts' | 'reports' | 'activity' | 'chat' | 'emergency' | 'smarthome' | 'rpm' | 'settings';

const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: 'alerts', label: 'Alerts', icon: <AlertTriangle className="w-5 h-5" /> },
  { id: 'reports', label: 'Reports', icon: <BarChart3 className="w-5 h-5" /> },
  { id: 'activity', label: 'Activity', icon: <Activity className="w-5 h-5" /> },
  { id: 'chat', label: 'Chat', icon: <MessageCircle className="w-5 h-5" /> },
  { id: 'emergency', label: 'Emergency', icon: <Phone className="w-5 h-5" /> },
  { id: 'smarthome', label: 'Smart Home', icon: <Home className="w-5 h-5" /> },
  { id: 'rpm', label: 'Devices', icon: <Activity className="w-5 h-5" /> },
  { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
];

const FamilyDashboard: React.FC = () => {
  const [activePage, setActivePage] = useState<Page>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuthStore();
  const { alerts, loadDashboardData } = useFamilyStore();
  const familyUser = user as FamilyProfile | null;
  const activeAlerts = alerts.filter(a => a.status === 'active').length;
  const initials = user?.name?.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase() ?? 'F';
  const currentLabel = navItems.find(n => n.id === activePage)?.label ?? '';

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  // Lock body scroll when drawer open on mobile
  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = ''; };
    }
  }, [sidebarOpen]);

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <FamilyDashboardContent />;
      case 'alerts': return <AlertsPage />;
      case 'reports': return <ReportsPage />;
      case 'activity': return <ActivityTimelinePage />;
      case 'chat': return <ChatVisibilityPage />;
      case 'emergency': return <EmergencyTelehealthPage />;
      case 'smarthome': return <SmartHomeFamilyPage />;
      case 'rpm': return <RPMDevicesPage />;
      case 'settings': return <SettingsPage />;
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 sm:w-64 bg-family-sidebar transform transition-transform duration-200 ease-out lg:relative lg:translate-x-0 lg:w-64 shadow-2xl lg:shadow-none ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
        aria-label="Primary navigation"
      >
        <div className="flex flex-col h-full">
          <div className="p-5 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center shrink-0">
              <Heart className="w-5 h-5 text-family-sidebar-active" />
            </div>
            <span className="font-heading text-lg font-bold text-family-sidebar-foreground truncate">ConnectedCare+</span>
            <button onClick={() => setSidebarOpen(false)} aria-label="Close menu" className="ml-auto lg:hidden text-family-sidebar-foreground/70 hover:text-family-sidebar-foreground p-1.5 rounded-md hover:bg-sidebar-accent transition-colors focus-ring">
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
            {navItems.map(item => (
              <button
                key={item.id}
                onClick={() => { setActivePage(item.id); setSidebarOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors focus-ring ${
                  activePage === item.id
                    ? 'bg-family-sidebar-active/15 text-family-sidebar-active'
                    : 'text-family-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-family-sidebar-foreground'
                }`}
                aria-current={activePage === item.id ? 'page' : undefined}
              >
                <span className="shrink-0">{item.icon}</span>
                <span className="truncate">{item.label}</span>
                {item.id === 'alerts' && activeAlerts > 0 && (
                  <span className="ml-auto bg-destructive text-destructive-foreground text-[10px] font-bold min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center">
                    {activeAlerts}
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="p-4 border-t border-sidebar-border">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-primary/20 text-family-sidebar-active flex items-center justify-center text-xs font-semibold shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-family-sidebar-foreground truncate">{user?.name ?? 'Family member'}</p>
                <p className="text-[10px] text-family-sidebar-foreground/50">Family member</p>
              </div>
              <button onClick={logout} aria-label="Log out" className="text-family-sidebar-foreground/50 hover:text-family-sidebar-foreground p-1.5 rounded-md hover:bg-sidebar-accent transition-colors focus-ring">
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-foreground/40 backdrop-blur-sm z-40 lg:hidden" onClick={() => setSidebarOpen(false)} aria-hidden />
      )}

      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Header */}
        <header className="bg-card/95 backdrop-blur border-b border-border sticky top-0 z-30">
          <div className="px-4 sm:px-6 py-3 flex items-center justify-between gap-3 max-w-7xl mx-auto w-full">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <button
                onClick={() => setSidebarOpen(true)}
                aria-label="Open menu"
                className="lg:hidden p-2 -ml-2 rounded-md hover:bg-muted transition-colors focus-ring"
              >
                <Menu className="w-5 h-5 text-foreground" />
              </button>

              {/* Page title (mobile) */}
              <h1 className="font-heading text-base font-bold text-foreground sm:hidden truncate">{currentLabel}</h1>

              {/* Elder selector (sm+) */}
              <button className="hidden sm:flex items-center gap-2 bg-muted hover:bg-muted/70 rounded-xl px-3 py-1.5 transition-colors focus-ring">
                <div className="w-7 h-7 rounded-full bg-primary/15 text-primary flex items-center justify-center text-[11px] font-semibold">MJ</div>
                <div className="leading-tight text-left">
                  <p className="text-sm font-medium text-foreground">Margaret Johnson</p>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    <span className="text-[10px] text-muted-foreground">Online · just now</span>
                  </div>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground ml-1" />
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button aria-label="Notifications" className="relative w-9 h-9 rounded-xl bg-muted flex items-center justify-center hover:bg-muted/70 transition-colors focus-ring">
                <Bell className="w-4 h-4 text-foreground" />
                {activeAlerts > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 bg-destructive text-destructive-foreground text-[9px] font-bold rounded-full flex items-center justify-center">
                    {activeAlerts}
                  </span>
                )}
              </button>
              <button aria-label="Emergency call" className="w-9 h-9 rounded-xl bg-destructive/10 text-destructive flex items-center justify-center hover:bg-destructive/15 transition-colors focus-ring">
                <Phone className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Compact elder chip on mobile */}
          <div className="sm:hidden px-4 pb-3 -mt-1">
            <div className="flex items-center gap-2 bg-muted rounded-xl px-3 py-2">
              <div className="w-7 h-7 rounded-full bg-primary/15 text-primary flex items-center justify-center text-[11px] font-semibold shrink-0">MJ</div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate">Margaret Johnson · 78</p>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-success" />
                  <span className="text-[10px] text-muted-foreground">Online</span>
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="p-4 sm:p-6 max-w-7xl mx-auto w-full">
            {renderPage()}
          </div>
        </main>
      </div>
    </div>
  );
};

export default FamilyDashboard;


