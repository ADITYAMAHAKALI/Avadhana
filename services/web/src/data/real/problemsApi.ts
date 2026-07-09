import type { Problem, Tier } from '../../types/domain';
import { apiFetch } from './httpClient';

export interface CreateProblemPayload {
  title: string;
  summary: string;
  location: string;
  category: string;
  tier: Tier;
}

/**
 * Problem creation isn't part of ProblemsPort — that port is deliberately
 * read-only (listDiscoverable/getById/getTasks/getFeed/getGraph), matching
 * the pattern commitmentsApi.ts already established for authenticated write
 * actions that don't fit a read port. POST /problems requires auth (any
 * authenticated user, not just committed members — creating a problem IS
 * the discovery mechanic, see CLAUDE.md "Problem Creation").
 */
export const problemsApi = {
  async create(payload: CreateProblemPayload): Promise<Problem> {
    return apiFetch<Problem>('/problems', { method: 'POST', body: payload });
  },
};
