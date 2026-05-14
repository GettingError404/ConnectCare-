import { NextRequest, NextResponse } from 'next/server';
import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE_KEY,
  SUPPORTED_LOCALES,
  getLocaleFromPathname,
  isSupportedLocale,
} from './src/lib/locale';

function shouldSkipPath(pathname: string): boolean {
  if (pathname.startsWith('/api')) return true;
  if (pathname.startsWith('/_next')) return true;
  if (pathname.startsWith('/favicon.ico')) return true;
  if (pathname.startsWith('/sw.js')) return true;
  if (pathname.startsWith('/workbox-')) return true;
  if (pathname.includes('.')) return true;
  return false;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (shouldSkipPath(pathname)) {
    return NextResponse.next();
  }

  const localeInPath = getLocaleFromPathname(pathname);
  if (localeInPath) {
    const rewrittenPath = pathname.replace(new RegExp(`^/${localeInPath}`), '') || '/';
    const rewriteUrl = request.nextUrl.clone();
    rewriteUrl.pathname = rewrittenPath;

    const response = NextResponse.rewrite(rewriteUrl);
    response.cookies.set(LOCALE_COOKIE_KEY, localeInPath, { path: '/', sameSite: 'lax' });
    return response;
  }

  const localeCookie = request.cookies.get(LOCALE_COOKIE_KEY)?.value;
  if (isSupportedLocale(localeCookie) && localeCookie !== DEFAULT_LOCALE) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = pathname === '/' ? `/${localeCookie}` : `/${localeCookie}${pathname}`;
    return NextResponse.redirect(redirectUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
