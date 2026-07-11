import type { User } from '../types/domain';
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

/** Mirrors services/web/src/data/real/authApi.ts — same endpoints, same payload shapes. */
export const authApi = {
  async signup(payload: SignupPayload): Promise<AuthResponse> {
    return apiFetch<AuthResponse>('/auth/signup', { method: 'POST', body: payload, auth: false });
  },

  async login(payload: LoginPayload): Promise<AuthResponse> {
    return apiFetch<AuthResponse>('/auth/login', { method: 'POST', body: payload, auth: false });
  },
};
