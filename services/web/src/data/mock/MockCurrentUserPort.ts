import type { CurrentUserPort } from '../interfaces';
import { COMMITMENT_HISTORY, COMMITTED_PROBLEMS, CURRENT_USER } from './fixtures';

export class MockCurrentUserPort implements CurrentUserPort {
  async getCurrentUser() {
    return CURRENT_USER;
  }

  async getFocusSlotCount() {
    return { used: COMMITTED_PROBLEMS.length, total: 3 };
  }

  async getCommittedProblems() {
    return COMMITTED_PROBLEMS;
  }

  async getCommitmentHistory() {
    return COMMITMENT_HISTORY;
  }
}
