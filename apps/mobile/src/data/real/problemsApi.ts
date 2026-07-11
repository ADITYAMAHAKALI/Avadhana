import type { FeedPost, Problem, Tier } from '../types/domain';
import { apiFetch, ApiError } from './httpClient';

export interface DiscoverFilters {
  q?: string;
  tier?: Tier;
  location?: string;
  category?: string;
}

/**
 * Mirrors services/web/src/data/real/RealProblemsPort.ts — same endpoints.
 * Read-only for now: problem creation and gated feed writes (post/comment/
 * like) come with #90-#92, not this scaffold.
 */
export const problemsApi = {
  async listDiscoverable(filters: DiscoverFilters = {}): Promise<Problem[]> {
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.tier) params.set('tier', filters.tier);
    if (filters.location) params.set('location', filters.location);
    if (filters.category) params.set('category', filters.category);
    const qs = params.toString();
    return apiFetch<Problem[]>(`/problems${qs ? `?${qs}` : ''}`, { auth: false });
  },

  async getById(problemId: string): Promise<Problem | null> {
    try {
      return await apiFetch<Problem>(`/problems/${problemId}`, { auth: false });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        return null;
      }
      throw err;
    }
  },

  async getFeed(problemId: string): Promise<FeedPost[]> {
    return apiFetch<FeedPost[]>(`/problems/${problemId}/posts`, { auth: false });
  },
};
