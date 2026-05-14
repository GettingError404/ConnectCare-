export const SUPPORTED_LOCALES = ['en', 'hi', 'mr', 'kn'] as const;

export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: AppLocale = 'en';

export const LOCALE_STORAGE_KEY = 'cc_locale';
export const LOCALE_COOKIE_KEY = 'cc_locale';

export const LOCALE_LABELS: Record<AppLocale, string> = {
  en: 'English',
  hi: 'Hindi',
  mr: 'Marathi',
  kn: 'Kannada',
};

export function isSupportedLocale(value: string | null | undefined): value is AppLocale {
  if (!value) return false;
  return SUPPORTED_LOCALES.includes(value as AppLocale);
}

export function getLocaleFromPathname(pathname: string): AppLocale | null {
  const segment = pathname.split('/').filter(Boolean)[0] ?? null;
  return isSupportedLocale(segment) ? segment : null;
}

export function stripLocaleFromPathname(pathname: string): string {
  const locale = getLocaleFromPathname(pathname);
  if (!locale) return pathname || '/';

  const stripped = pathname.replace(new RegExp(`^/${locale}`), '');
  return stripped === '' ? '/' : stripped;
}

export function localizePathname(pathname: string, locale: AppLocale): string {
  const barePath = stripLocaleFromPathname(pathname || '/');
  if (locale === DEFAULT_LOCALE) return barePath;
  if (barePath === '/') return `/${locale}`;
  return `/${locale}${barePath}`;
}
