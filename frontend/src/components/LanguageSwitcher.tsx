'use client';

import { Languages } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
  LOCALE_COOKIE_KEY,
  LOCALE_LABELS,
  LOCALE_STORAGE_KEY,
  SUPPORTED_LOCALES,
  type AppLocale,
  getLocaleFromPathname,
  localizePathname,
} from '@/lib/locale';

type LanguageSwitcherProps = {
  label: string;
  helperText: string;
};

export default function LanguageSwitcher({ label, helperText }: LanguageSwitcherProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  const currentLocale = (getLocaleFromPathname(pathname || '') ?? 'en') as AppLocale;

  const updateLanguage = (value: string) => {
    const nextLocale = value as AppLocale;
    const nextPath = localizePathname(pathname || '/', nextLocale);
    const nextSearch = searchParams.toString();
    const destination = nextSearch ? `${nextPath}?${nextSearch}` : nextPath;

    window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    document.cookie = `${LOCALE_COOKIE_KEY}=${nextLocale}; path=/; samesite=lax`;
    router.replace(destination);
  };

  return (
    <div className="bg-card rounded-xl border border-border p-4 shadow-sm" aria-label="Language switcher">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center" aria-hidden>
          <Languages className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{helperText}</p>
          <select
            aria-label={label}
            className="mt-3 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            value={currentLocale}
            onChange={(event) => updateLanguage(event.target.value)}
          >
            {SUPPORTED_LOCALES.map((locale) => (
              <option key={locale} value={locale}>
                {LOCALE_LABELS[locale]}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
