import type { ApiResponse } from '@/lib/api/types';
import { API_BASE_URL } from './config';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const CC_USER_KEY = 'cc_user';

type JsonLike = Record<string, unknown> | string | number | boolean | null;

type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
};

const isBrowser = typeof window !== 'undefined';

export function getAccessToken(): string | null {
  if (!isBrowser) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (!isBrowser) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  if (!isBrowser) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(CC_USER_KEY);
}

let refreshInFlight: Promise<TokenPair> | null = null;

async function refreshTokens(): Promise<TokenPair> {
  if (!isBrowser) {
    throw new Error('Cannot refresh tokens on server');
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const payload = (await response.json()) as ApiResponse<TokenPair>;
    if (!payload || payload.ok !== true) {
      throw new Error(payload && 'error' in payload ? payload.error.message : 'Refresh failed');
    }

    const { access_token, refresh_token } = payload.data;
    setTokens(access_token, refresh_token);
    return payload.data;
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

async function parseApiResponse<T>(response: Response): Promise<ApiResponse<T>> {
  try {
    return (await response.json()) as ApiResponse<T>;
  } catch {
    return {
      ok: false,
      error: {
        code: 'INVALID_JSON',
        message: 'Invalid JSON response',
        details: null,
      },
    };
  }
}

export async function apiClient<T>(input: RequestInfo | URL, init?: RequestInit): Promise<ApiResponse<T>> {
  const requestInit: RequestInit = { ...(init || {}) };

  // Add Authorization header (best effort)
  const headers = new Headers(requestInit.headers || {});
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const accessToken = getAccessToken();
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  requestInit.headers = headers;

  const performRequest = async () => {
    const response = await fetch(input, requestInit);
    return { response, parsed: await parseApiResponse<T>(response) };
  };

  try {
    const { response, parsed } = await performRequest();

    if (response.status !== 401) {
      return parsed;
    }

    // Avoid infinite loops
    const retryFlagKey = '__cc_refresh_attempted__';
    const alreadyRetried = (requestInit as Record<string, unknown>)[retryFlagKey] === true;
    if (alreadyRetried) {
      clearTokens();
      if (isBrowser) window.location.replace('/login');
      return parsed;
    }

    if (!getRefreshToken()) {
      clearTokens();
      if (isBrowser) window.location.replace('/login');
      return parsed;
    }

    // Mark and refresh
    (requestInit as Record<string, unknown>)[retryFlagKey] = true;
    const newTokens = await refreshTokens();

    // Update Authorization header with refreshed token
    requestInit.headers = new Headers(headers);
    requestInit.headers.set('Authorization', `Bearer ${newTokens.access_token}`);

    const { parsed: retriedParsed } = await performRequest();
    return retriedParsed;
  } catch (error) {
    return {
      ok: false,
      error: {
        code: 'NETWORK_ERROR',
        message: 'Unable to reach the server',
        details: error,
      },
    };
  }
}

