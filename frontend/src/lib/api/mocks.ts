import type { ApiResponse } from '@/lib/api/types';

export function mockSuccess<T>(data: T, meta?: Record<string, unknown>): ApiResponse<T> {
  return {
    ok: true,
    data,
    meta,
  };
}

export function mockFailure(code: string, message: string, details?: unknown): ApiResponse<never> {
  return {
    ok: false,
    error: {
      code,
      message,
      details,
    },
  };
}
