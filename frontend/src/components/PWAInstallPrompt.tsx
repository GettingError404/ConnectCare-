'use client';

import { useEffect, useState } from 'react';
import { Download, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
};

type PWAInstallPromptProps = {
  title: string;
  description: string;
};

export default function PWAInstallPrompt({ title, description }: PWAInstallPromptProps) {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };

    const onInstalled = () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt);
    window.addEventListener('appinstalled', onInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
  };

  if (isInstalled || !deferredPrompt) return null;

  return (
    <div className="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center" aria-hidden>
          <Smartphone className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
          <Button onClick={handleInstall} variant="outline" className="mt-3 w-full sm:w-auto" aria-label={title}>
            <Download className="w-4 h-4 mr-2" />
            Install app
          </Button>
        </div>
      </div>
    </div>
  );
}
