import type { ActorSpecialization, CommitmentStatus, Role } from '../../types/domain';
import { apiFetch } from './httpClient';

export interface CreateCommitmentPayload {
  role: Role;
  specialization: ActorSpecialization | null;
}

export interface Commitment {
  id: string;
  problemId: string;
  role: Role;
  specialization: ActorSpecialization | null;
  status: CommitmentStatus;
  startedAt: string;
  lockExpiresAt: string;
  createdAt: string;
}

export type CheckpointAction = 'resolve' | 'abandon' | 'continue';

/**
 * Commitments aren't part of CurrentUserPort/ProblemsPort — neither port
 * models a "write" for spending a focus slot, and adding one would have
 * meant widening both interfaces for a single call site (CommitModal).
 * Kept as a standalone module the same way auth is, and called directly
 * from CommitModal.
 */
export const commitmentsApi = {
  async create(problemId: string, payload: CreateCommitmentPayload): Promise<Commitment> {
    return apiFetch<Commitment>(`/problems/${problemId}/commitments`, { method: 'POST', body: payload });
  },

  /**
   * Wired to CheckpointModal (services/web/src/components/CheckpointModal).
   * On success (200) the backend returns the updated Commitment; before the
   * 90-day lock expires it instead responds 409
   * `{error: "LOCK_ACTIVE", message, daysRemaining}` — callers should catch
   * ApiError and read `.body` for `daysRemaining` in that case.
   */
  async checkpoint(commitmentId: string, action: CheckpointAction, note: string | null): Promise<Commitment> {
    return apiFetch<Commitment>(`/commitments/${commitmentId}/checkpoint`, {
      method: 'POST',
      body: { action, note },
    });
  },
};
