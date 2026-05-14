import React from 'react';
import { Phone, Video, Calendar, Clock, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

const EmergencyTelehealthPage: React.FC = () => {
  const appointments = [
    { id: 1, doctor: 'Dr. Williams', specialty: 'General Physician', date: 'Tomorrow, 10:00 AM', type: 'Regular Checkup' },
    { id: 2, doctor: 'Dr. Patel', specialty: 'Cardiologist', date: 'Next Monday, 2:30 PM', type: 'BP Follow-up' },
  ];

  const consultHistory = [
    { id: 1, doctor: 'Dr. Williams', date: '2024-03-01', summary: 'Routine checkup. BP slightly elevated. Adjusted medication.' },
    { id: 2, doctor: 'Dr. Patel', date: '2024-02-15', summary: 'Cardiac review. EKG normal. Continue current treatment.' },
  ];

  return (
    <div className="space-y-6 pb-8">
      <div>
        <h2 className="font-heading text-xl font-bold text-foreground mb-1">Emergency & Telehealth</h2>
        <p className="text-sm text-muted-foreground">Quick access to emergency services and consultations</p>
      </div>

      {/* Emergency Actions */}
      <div className="bg-destructive/5 border-2 border-destructive/20 rounded-2xl p-5">
        <h3 className="font-heading text-base font-semibold text-destructive mb-3 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" /> Emergency Actions
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <Button variant="destructive" className="h-14 text-base">
            <Phone className="w-5 h-5 mr-2" /> Call 911
          </Button>
          <Button variant="outline" className="h-14 text-base border-destructive/30 text-destructive hover:bg-destructive/10">
            <Phone className="w-5 h-5 mr-2" /> Call Dr. Williams
          </Button>
        </div>
      </div>

      {/* Quick Call */}
      <div className="grid grid-cols-2 gap-3">
        <Button variant="outline" className="h-14">
          <Video className="w-5 h-5 mr-2" /> Video Call Margaret
        </Button>
        <Button variant="outline" className="h-14">
          <Phone className="w-5 h-5 mr-2" /> Audio Call Margaret
        </Button>
      </div>

      {/* Upcoming Appointments */}
      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3">Upcoming Appointments</h3>
        <div className="space-y-3">
          {appointments.map(apt => (
            <div key={apt.id} className="bg-card rounded-xl border border-border p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">{apt.doctor}</p>
                  <p className="text-xs text-muted-foreground">{apt.specialty} · {apt.type}</p>
                </div>
                <Button size="sm">Start</Button>
              </div>
              <p className="text-sm text-primary mt-2 flex items-center gap-1">
                <Calendar className="w-3 h-3" /> {apt.date}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Consultation History */}
      <div>
        <h3 className="font-heading text-base font-semibold text-foreground mb-3">Consultation History</h3>
        <div className="space-y-2">
          {consultHistory.map(c => (
            <div key={c.id} className="bg-card rounded-xl border border-border p-4 shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium text-foreground">{c.doctor}</p>
                <p className="text-xs text-muted-foreground">{c.date}</p>
              </div>
              <p className="text-xs text-muted-foreground">{c.summary}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default EmergencyTelehealthPage;
