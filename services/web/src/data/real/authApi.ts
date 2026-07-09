import type { User } from '../../types/domain';
import { apiFetch } from './httpClient';

export interface AuthResponse {
  token: string;
  user: User;
}

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
  location: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

/**
 * Auth isn't part of CurrentUserPort/ProblemsPort (those assume an
 * already-authenticated session) — it's a small standalone module that
 * AuthContext calls directly, mirroring how the mock ports never modeled
 * auth either (the mock app just started "logged in").
 */
export const authApi = {
  async signup(payload: SignupPayload): Promise<AuthResponse> {
    return apiFetch<AuthResponse>('/auth/signup', { method: 'POST', body: payload, auth: false });
  },

  async login(payload: LoginPayload): Promise<AuthResponse> {
    return apiFetch<AuthResponse>('/auth/login', { method: 'POST', body: payload, auth: false });
  },
};
