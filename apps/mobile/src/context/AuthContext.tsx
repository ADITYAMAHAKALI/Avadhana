import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import type { User } from '../data/types/domain';
import { authApi, type LoginPayload, type SignupPayload } from '../data/real/authApi';
import {
  ApiError,
  clearStoredToken,
  getStoredToken,
  registerSessionExpiredHandler,
  setStoredToken,
} from '../data/real/httpClient';
import { currentUserApi } from '../data/real/currentUserApi';

interface AuthContextValue {
  /** True until the initial expo-secure-store read has resolved. Root layout should hold the splash screen until this flips false. */
  isBootstrapping: boolean;
  isAuthenticated: boolean;
  /** The signed-in user, fetched once at bootstrap/login/signup and cached here so screens don't all need to re-fetch it. Null until known. */
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
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
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

  // expo-secure-store reads are async (unlike web's synchronous localStorage),
  // so there's a real bootstrap step: check for an existing token, and if one
  // exists, fetch the user before deciding where the app should route.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await getStoredToken();
      if (!token) {
        if (!cancelled) setIsBootstrapping(false);
        return;
      }
      try {
        const user = await currentUserApi.getCurrentUser();
        if (cancelled) return;
        setCurrentUser(user);
        setIsAuthenticated(true);
      } catch {
        // Token invalid/expired — apiFetch's 401 handling already cleared it.
      } finally {
        if (!cancelled) setIsBootstrapping(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isBootstrapping,
      isAuthenticated,
      currentUser,
      isAuthenticating,
      authError,

      async login(credentials: LoginPayload) {
        setIsAuthenticating(true);
        setAuthError(null);
        try {
          const { token, user } = await authApi.login(credentials);
          await setStoredToken(token);
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
        setIsAuthenticating(true);
        setAuthError(null);
        try {
          const { token, user } = await authApi.signup(payload);
          await setStoredToken(token);
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
        void clearStoredToken();
        setIsAuthenticated(false);
        setCurrentUser(null);
      },

      clearAuthError() {
        setAuthError(null);
      },
    }),
    [isBootstrapping, isAuthenticated, currentUser, isAuthenticating, authError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
