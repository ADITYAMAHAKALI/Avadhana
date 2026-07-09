import type { ProblemsPort } from '../interfaces';
import type { FeedPost, Problem, ProblemGraphEdge, ProblemGraphNode, TaskItem } from '../../types/domain';
import { apiFetch, ApiError } from './httpClient';

export interface DiscoverFilters {
  q?: string;
  tier?: string;
  location?: string;
  category?: string;
}

export class RealProblemsPort implements ProblemsPort {
  /**
   * Contract supports q/tier/location/category query params, but no screen
   * currently wires filter UI through to this call — DiscoverPage's tier
   * buttons and search bar are presentational only today. Accepting an
   * optional `filters` arg (not part of the ProblemsPort interface) lets a
   * future screen opt in without another port change; called with none, this
   * is just the unfiltered list per the v1 instruction.
   */
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

  async getFeed(problemId: string): Promise<FeedPost[]> {
    return apiFetch<FeedPost[]>(`/problems/${problemId}/posts`, { auth: false });
  }

  /** No backend support yet (problem hierarchy/merge graph deferred) — degrade gracefully instead of throwing. */
  async getGraph(_problemId: string): Promise<{ nodes: ProblemGraphNode[]; edges: ProblemGraphEdge[] }> {
    return { nodes: [], edges: [] };
  }
}
