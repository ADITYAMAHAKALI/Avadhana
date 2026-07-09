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
   * Not wired to any UI yet — no checkpoint-flow screen exists in the
   * current mockup (per the task's scope boundaries). Included so the
   * endpoint is ready for that screen later.
   */
  async checkpoint(commitmentId: string, action: CheckpointAction, note: string): Promise<void> {
    await apiFetch<void>(`/commitments/${commitmentId}/checkpoint`, { method: 'POST', body: { action, note } });
  },
};
