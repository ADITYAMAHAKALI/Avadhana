import type { CommitmentHistoryEntry, CommittedProblemSummary, User } from '../types/domain';
import { apiFetch } from './httpClient';

/** Mirrors services/web/src/data/real/RealCurrentUserPort.ts — same endpoints. */
export const currentUserApi = {
  async getCurrentUser(): Promise<User> {
    return apiFetch<User>('/users/me');
  },

  async getFocusSlotCount(): Promise<{ used: number; total: number }> {
    return apiFetch<{ used: number; total: number }>('/users/me/focus-slots');
  },

  async getCommittedProblems(): Promise<CommittedProblemSummary[]> {
    return apiFetch<CommittedProblemSummary[]>('/users/me/committed-problems');
  },

  async getCommitmentHistory(): Promise<CommitmentHistoryEntry[]> {
    return apiFetch<CommitmentHistoryEntry[]>('/users/me/commitment-history');
  },
};
