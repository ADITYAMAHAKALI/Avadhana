import type { DiscoverFilters, ProblemsPort } from '../interfaces';
import type { FeedPost, FeedSort, Problem, ProblemGraphEdge, ProblemGraphNode, TaskItem } from '../../types/domain';
import { apiFetch, ApiError } from './httpClient';

export type { DiscoverFilters };

export class RealProblemsPort implements ProblemsPort {
  /** Backend supports q/tier/location/category query params (all optional); DiscoverPage now wires real filter UI through to this call. */
  async listDiscoverable(filters: DiscoverFilters = {}): Promise<Problem[]> {
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.tier) params.set('tier', filters.tier);
    if (filters.location) params.set('location', filters.location);
    if (filters.category) params.set('category', filters.category);
    const qs = params.toString();
    return apiFetch<Problem[]>(`/problems${qs ? `?${qs}` : ''}`, { auth: false });
  }

  async getById(problemId: string): Promise<Problem | null> {
    try {
      return await apiFetch<Problem>(`/problems/${problemId}`, { auth: false });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        return null;
      }
      throw err;
    }
  }

  /** No backend support yet (task board deferred) — degrade gracefully instead of throwing. */
  async getTasks(_problemId: string): Promise<TaskItem[]> {
    return [];
  }

  async getFeed(problemId: string, sort: FeedSort = 'new'): Promise<FeedPost[]> {
    return apiFetch<FeedPost[]>(`/problems/${problemId}/posts?sort=${sort}`, { auth: false });
  }

  /** No backend support yet (problem hierarchy/merge graph deferred) — degrade gracefully instead of throwing. */
  async getGraph(_problemId: string): Promise<{ nodes: ProblemGraphNode[]; edges: ProblemGraphEdge[] }> {
    return { nodes: [], edges: [] };
  }
}
