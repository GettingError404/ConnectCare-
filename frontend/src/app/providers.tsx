'use client';

import { ReactNode, useEffect, useMemo } from 'react';
import { ThemeProvider } from 'next-themes';
import { QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { usePathname } from 'next/navigation';
import enMessages from '@/messages/en.json';
import hiMessages from '@/messages/hi.json';
import mrMessages from '@/messages/mr.json';
import knMessages from '@/messages/kn.json';
import { queryClient } from '@/lib/queryClient';
import { SocketProvider } from '@/services/socket';
import { Toaster as SonnerToaster } from '@/components/ui/sonner';
import { Toaster } from '@/components/ui/toaster';
import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE_KEY,
  LOCALE_STORAGE_KEY,
  type AppLocale,
  getLocaleFromPathname,
  isSupportedLocale,
} from '@/lib/locale';

const MESSAGES: Record<AppLocale, Record<string, unknown>> = {
  en: enMessages,
  hi: hiMessages,
  mr: mrMessages,
  kn: knMessages,
};

function readStoredLocale(): AppLocale {
  if (typeof window === 'undefined') return DEFAULT_LOCALE;

  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  if (isSupportedLocale(stored)) return stored;

  const fromCookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${LOCALE_COOKIE_KEY}=`))
    ?.split('=')[1];

  if (isSupportedLocale(fromCookie)) return fromCookie;
  return DEFAULT_LOCALE;
}

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const pathname = usePathname();

  const locale = useMemo<AppLocale>(() => {
    const pathLocale = pathname ? getLocaleFromPathname(pathname) : null;
    return pathLocale ?? readStoredLocale();
  }, [pathname]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    document.cookie = `${LOCALE_COOKIE_KEY}=${locale}; path=/; samesite=lax`;
    document.documentElement.lang = locale;
  }, [locale]);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        <SocketProvider>
          <NextIntlClientProvider locale={locale} messages={MESSAGES[locale]}>
            {children}
          </NextIntlClientProvider>
          <Toaster />
          <SonnerToaster />
        </SocketProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
