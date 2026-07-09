import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { User } from '../types/domain';
import { authApi, type LoginPayload, type SignupPayload } from '../data/real/authApi';
import {
  ApiError,
  clearStoredToken,
  getStoredToken,
  registerSessionExpiredHandler,
  setStoredToken,
} from '../data/real/httpClient';
import { currentUserPort } from '../data';

/**
 * Whether real auth (signup/login hitting the backend) is available. Mirrors
 * the mock/real toggle in data/index.ts: without VITE_API_BASE_URL there's
 * no backend to authenticate against, so the app falls back to a mock
 * "already logged in" session — same behavior as before this pass, just
 * gated explicitly instead of being the only option.
 */
const AUTH_BACKED_BY_API = Boolean(import.meta.env.VITE_API_BASE_URL) && import.meta.env.VITE_USE_MOCK_DATA !== 'true';

interface AuthContextValue {
  isAuthenticated: boolean;
  /** The signed-in user, fetched once at login/signup and cached here so screens don't all need to re-fetch it. Null until known. */
  currentUser: User | null;
  /** True while a login/signup request is in flight. */
  isAuthenticating: boolean;
  /** Error message from the last failed login/signup attempt, if any. */
  authError: string | null;
  login: (credentials: LoginPayload) => Promise<void>;
  signup: (payload: SignupPayload) => Promise<void>;
  logout: () => void;
  clearAuthError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // In mock mode there's no login screen friction to preserve — start "logged in" like before.
  const [isAuthenticated, setIsAuthenticated] = useState(() => !AUTH_BACKED_BY_API || Boolean(getStoredToken()));
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Register the 401 handler once so any apiFetch call anywhere in the app can force a logout.
  useEffect(() => {
    registerSessionExpiredHandler(() => {
      setIsAuthenticated(false);
      setCurrentUser(null);
    });
  }, []);

  // If we already have a token (e.g. page refresh), fetch the user once so context is populated.
  useEffect(() => {
    if (!AUTH_BACKED_BY_API || !isAuthenticated || currentUser) return;
    let cancelled = false;
    currentUserPort
      .getCurrentUser()
      .then((user) => {
        if (!cancelled) setCurrentUser(user);
      })
      .catch(() => {
        // Token invalid/expired — apiFetch's 401 handling already cleared it and flipped isAuthenticated.
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      currentUser,
      isAuthenticating,
      authError,

      async login(credentials: LoginPayload) {
        if (!AUTH_BACKED_BY_API) {
          setIsAuthenticated(true);
          return;
        }
        setIsAuthenticating(true);
        setAuthError(null);
        try {
          const { token, user } = await authApi.login(credentials);
          setStoredToken(token);
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch (err) {
          const message =
            err instanceof ApiError && err.status === 401
              ? 'Invalid email or password.'
              : err instanceof ApiError
                ? err.message
                : 'Something went wrong logging in. Please try again.';
          setAuthError(message);
          throw err;
        } finally {
          setIsAuthenticating(false);
        }
      },

      async signup(payload: SignupPayload) {
        if (!AUTH_BACKED_BY_API) {
          setIsAuthenticated(true);
          return;
        }
        setIsAuthenticating(true);
        setAuthError(null);
        try {
          const { token, user } = await authApi.signup(payload);
          setStoredToken(token);
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch (err) {
          const message = err instanceof ApiError ? err.message : 'Something went wrong creating your account. Please try again.';
          setAuthError(message);
          throw err;
        } finally {
          setIsAuthenticating(false);
        }
      },

      logout() {
        clearStoredToken();
        setIsAuthenticated(false);
        setCurrentUser(null);
      },

      clearAuthError() {
        setAuthError(null);
      },
    }),
    [isAuthenticated, currentUser, isAuthenticating, authError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
