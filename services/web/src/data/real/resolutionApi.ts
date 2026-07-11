import { PROBLEMS } from '../mock/fixtures';
import { apiFetch } from './httpClient';

/**
 * Resolution-objection write action (issue #100) — standalone module,
 * same convention as feedApi.ts/commitmentsApi.ts. Not part of
 * ProblemsPort (that interface stays read-only, see its docstring in
 * ../interfaces.ts).
 *
 * Mock mode has no real per-user "did I already object" tracking or
 * window math — it just bumps the matching PROBLEMS fixture's
 * objectionCount and flips resolutionStatus to 'disputed', good enough
 * for `npm run dev` without a backend.
 */
const hasApiBaseUrl = Boolean(import.meta.env.VITE_API_BASE_URL);
const forceMock = import.meta.env.VITE_USE_MOCK_DATA === 'true';
const useReal = hasApiBaseUrl && !forceMock;

export interface ResolutionObjection {
  id: string;
  problemId: string;
  objectingUserId: string;
  raisedAt: string;
}

export const resolutionApi = {
  async objectToResolution(problemId: string): Promise<ResolutionObjection> {
    if (!useReal) {
      const problem = PROBLEMS.find((p) => p.id === problemId);
      if (problem) {
        problem.resolutionStatus = 'disputed';
        problem.objectionCount += 1;
      }
      return {
        id: `mock-objection-${Math.random().toString(36).slice(2, 9)}`,
        problemId,
        objectingUserId: 'mock-current-user',
        raisedAt: new Date().toISOString(),
      };
    }
    return apiFetch<ResolutionObjection>(`/problems/${problemId}/objections`, { method: 'POST' });
  },
};
