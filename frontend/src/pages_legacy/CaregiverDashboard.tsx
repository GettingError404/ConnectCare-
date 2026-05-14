'use client';
import React, { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useCaregiverStore } from '@/store/caregiverStore';
import {
  LayoutDashboard, AlertTriangle, ClipboardList, Users, Activity,
  FileText, ShieldCheck, Phone, LogOut, Bell, Menu, X,
  Stethoscope, History
} from 'lucide-react';
import CaregiverOverview from '@/components/caregiver/CaregiverOverview';
import CaregiverPatientsPage from '@/components/caregiver/CaregiverPatientsPage';
import CaregiverAlertsPage from '@/components/caregiver/CaregiverAlertsPage';
import CaregiverTasksPage from '@/components/caregiver/CaregiverTasksPage';
import CaregiverVitalsPage from '@/components/caregiver/CaregiverVitalsPage';
import CaregiverAWVPage from '@/components/caregiver/CaregiverAWVPage';
import CaregiverChronicCarePage from '@/components/caregiver/CaregiverChronicCarePage';
import CaregiverAlertHistoryPage from '@/components/caregiver/CaregiverAlertHistoryPage';
import CaregiverTelehealthPage from '@/components/caregiver/CaregiverTelehealthPage';

type Page = 'overview' | 'patients' | 'alerts' | 'tasks' | 'vitals' | 'awv' | 'chronic' | 'alert_history' | 'telehealth';

const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: 'patients', label: 'Patients', icon: <Users className="w-5 h-5" /> },
  { id: 'alerts', label: 'Alerts', icon: <AlertTriangle className="w-5 h-5" /> },
  { id: 'tasks', label: 'Care Tasks', icon: <ClipboardList className="w-5 h-5" /> },
  { id: 'vitals', label: 'Vitals Monitor', icon: <Activity className="w-5 h-5" /> },
  { id: 'awv', label: 'AWV Tracking', icon: <FileText className="w-5 h-5" /> },
  { id: 'chronic', label: 'Chronic Care', icon: <ShieldCheck className="w-5 h-5" /> },
  { id: 'alert_history', label: 'Alert History', icon: <History className="w-5 h-5" /> },
  { id: 'telehealth', label: 'Telehealth', icon: <Phone className="w-5 h-5" /> },
];

const CaregiverDashboard: React.FC = () => {
  const [activePage, setActivePage] = useState<Page>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuthStore();
  const { alerts, loadDashboardData } = useCaregiverStore();
  const activeAlerts = alerts.filter(a => a.status === 'active').length;
  const currentLabel = navItems.find(n => n.id === activePage)?.label ?? '';
  const initials = user?.name?.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase() ?? 'C';

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = ''; };
    }
  }, [sidebarOpen]);

  const renderPage = () => {
    switch (activePage) {
      case 'overview': return <CaregiverOverview onNavigate={setActivePage} />;
      case 'patients': return <CaregiverPatientsPage />;
      case 'alerts': return <CaregiverAlertsPage />;
      case 'tasks': return <CaregiverTasksPage />;
      case 'vitals': return <CaregiverVitalsPage />;
      case 'awv': return <CaregiverAWVPage />;
      case 'chronic': return <CaregiverChronicCarePage />;
      case 'alert_history': return <CaregiverAlertHistoryPage />;
      case 'telehealth': return <CaregiverTelehealthPage />;
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 sm:w-64 bg-family-sidebar transform transition-transform duration-200 ease-out lg:relative lg:translate-x-0 lg:w-64 shadow-2xl lg:shadow-none ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
        aria-label="Primary navigation"
      >
        <div className="flex flex-col h-full">
          <div className="p-5 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center shrink-0">
              <Stethoscope className="w-5 h-5 text-family-sidebar-active" />
            </div>
            <span className="font-heading text-lg font-bold text-family-sidebar-foreground truncate">CaregiverHub</span>
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
                <p className="text-sm font-medium text-family-sidebar-foreground truncate">{user?.name ?? 'Caregiver'}</p>
                <p className="text-[10px] text-family-sidebar-foreground/50">Care provider</p>
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
        <header className="bg-card/95 backdrop-blur border-b border-border sticky top-0 z-30">
          <div className="px-4 sm:px-6 py-3 flex items-center justify-between gap-3 max-w-7xl mx-auto w-full">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <button onClick={() => setSidebarOpen(true)} aria-label="Open menu" className="lg:hidden p-2 -ml-2 rounded-md hover:bg-muted transition-colors focus-ring">
                <Menu className="w-5 h-5 text-foreground" />
              </button>
              <h1 className="font-heading text-base sm:text-lg font-bold text-foreground truncate">{currentLabel}</h1>
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

export default CaregiverDashboard;


