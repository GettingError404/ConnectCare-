import { create } from 'zustand';
import { User, UserRole } from '@/types';
import { authService, type UserProfileResponse } from '@/lib/api/services/auth';

const isBrowser = typeof window !== 'undefined';

const readStorage = (key: string) => {
  if (!isBrowser) return null;
  return window.localStorage.getItem(key);
};

const writeStorage = (key: string, value: string) => {
  if (!isBrowser) return;
  window.localStorage.setItem(key, value);
};

const removeStorage = (key: string) => {
  if (!isBrowser) return;
  window.localStorage.removeItem(key);
};

const notifyAuthChanged = () => {
  if (!isBrowser) return;
  window.dispatchEvent(new Event('cc-auth-changed'));
};

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (name: string, email: string, password: string, role: UserRole, extra?: Record<string, unknown>) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
  setAccessToken: (token: string) => void;
  setRefreshToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: JSON.parse(readStorage('cc_user') || 'null'),
  isAuthenticated: !!readStorage('cc_user'),
  isLoading: false,
  error: null,
  accessToken: readStorage('access_token'),
  refreshToken: readStorage('refresh_token'),

  setAccessToken: (token: string) => {
    writeStorage('access_token', token);
    set({ accessToken: token });
    notifyAuthChanged();
  },

  setRefreshToken: (token: string) => {
    writeStorage('refresh_token', token);
    set({ refreshToken: token });
    notifyAuthChanged();
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.login({ email, password });
      if (!response.ok) {
        set({ error: response.error.message, isLoading: false });
        return false;
      }

      const { access_token, refresh_token } = response.data;
      writeStorage('access_token', access_token);
      writeStorage('refresh_token', refresh_token);

      const profileResponse = await authService.getCurrentUser();
      if (!profileResponse.ok) {
        set({ error: profileResponse.error.message ?? 'Failed to fetch profile', isLoading: false });
        return false;
      }

      const profile = profileResponse.data;
      const user: User = {
        id: profile.id,
        email: profile.email,
        name: profile.name,
        role: (profile.role ?? profile.roles?.[0] ?? 'elder') as UserRole,
        createdAt: profile.created_at,
      };

      writeStorage('cc_user', JSON.stringify(user));
      set({ user, isAuthenticated: true, isLoading: false, accessToken: access_token, refreshToken: refresh_token });
      notifyAuthChanged();
      return true;
    } catch (err) {
      set({ error: 'Failed to login', isLoading: false });
      return false;
    }
  },

  register: async (name, email, password, role, extra = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.register({ email, password, name });
      if (!response.ok) {
        set({ error: response.error.message, isLoading: false });
        return false;
      }

      const loginResponse = await authService.login({ email, password });
      if (!loginResponse.ok) {
        set({ error: loginResponse.error.message, isLoading: false });
        return false;
      }

      const { access_token, refresh_token } = loginResponse.data;
      writeStorage('access_token', access_token);
      writeStorage('refresh_token', refresh_token);

      const profileResponse = await authService.getCurrentUser();
      if (!profileResponse.ok) {
        set({ error: profileResponse.error.message ?? 'Failed to fetch profile', isLoading: false });
        return false;
      }

      const profile = profileResponse.data;
      const newUser: User = {
        id: profile.id,
        email: profile.email,
        name: profile.name,
        role: (profile.role ?? profile.roles?.[0] ?? role) as UserRole,
        createdAt: profile.created_at,
      };

      writeStorage('cc_user', JSON.stringify(newUser));
      set({ user: newUser, isAuthenticated: true, isLoading: false, accessToken: access_token, refreshToken: refresh_token });
      notifyAuthChanged();
      return true;
    } catch (err) {
      set({ error: 'Failed to register', isLoading: false });
      return false;
    }
  },

  logout: () => {
    const refreshToken = readStorage('refresh_token');
    if (refreshToken) {
      authService.logout(refreshToken).catch(err => console.error('Logout error:', err));
    }
    removeStorage('cc_user');
    removeStorage('access_token');
    removeStorage('refresh_token');
    set({ user: null, isAuthenticated: false, accessToken: null, refreshToken: null });
    notifyAuthChanged();
  },

  clearError: () => set({ error: null }),
}));
