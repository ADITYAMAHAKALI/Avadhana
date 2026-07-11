import type { DiscoverFilters, ProblemsPort } from '../interfaces';
import type { FeedSort, Problem } from '../../types/domain';
import {
  FEED_BY_PROBLEM,
  GRAPH_BY_PROBLEM,
  PROBLEMS,
  TASKS_BY_PROBLEM,
} from './fixtures';

let nextMockId = 1;

export class MockProblemsPort implements ProblemsPort {
  async listDiscoverable(filters: DiscoverFilters = {}) {
    const q = filters.q?.trim().toLowerCase();
    return PROBLEMS.filter((p) => {
      if (filters.tier && p.tier !== filters.tier) return false;
      if (filters.location && !p.location.toLowerCase().includes(filters.location.toLowerCase())) return false;
      if (filters.category && !p.category.toLowerCase().includes(filters.category.toLowerCase())) return false;
      if (q && !`${p.title} ${p.summary} ${p.location} ${p.category}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }

  async getById(problemId: string) {
    return PROBLEMS.find((p) => p.id === problemId) ?? null;
  }

  async getTasks(problemId: string) {
    return TASKS_BY_PROBLEM[problemId] ?? [];
  }

  /** `sort` (issue #98) mirrors the real backend's 'new'/'top' query
   * param so mock mode (`npm run dev`, zero backend) exercises the same
   * sort control the real API drives. No persisted `createdAt` timestamp
   * on mock fixtures (they use pre-rendered `timeAgo` strings instead),
   * so 'new' just returns fixture order (already newest-first by
   * convention) — 'top' re-sorts by likeCount desc, which is real data. */
  async getFeed(problemId: string, sort: FeedSort = 'new') {
    const posts = FEED_BY_PROBLEM[problemId] ?? [];
    if (sort === 'top') {
      return [...posts].sort((a, b) => b.likeCount - a.likeCount);
    }
    return posts;
  }

  async getGraph(problemId: string) {
    return GRAPH_BY_PROBLEM[problemId] ?? { nodes: [], edges: [] };
  }

  /**
   * Not part of ProblemsPort (that interface stays read-only). Mock-mode
   * counterpart to problemsApi.create — pushes into the in-memory fixture
   * list so the creation screen has something sensible to do under
   * `npm run dev` without a backend, per the task brief.
   */
  async createProblem(payload: Omit<Problem, 'id' | 'createdAt' | 'parentProblemTitle' | 'thinkerCount' | 'actorCount' | 'backerCount' | 'followingCount'>): Promise<Problem> {
    const problem: Problem = {
      id: `mock-${nextMockId++}`,
      title: payload.title,
      summary: payload.summary,
      location: payload.location,
      category: payload.category,
      tier: payload.tier,
      createdAt: new Date().toISOString(),
      parentProblemTitle: null,
      thinkerCount: 0,
      actorCount: 0,
      backerCount: 0,
      followingCount: 0,
    };
    PROBLEMS.unshift(problem);
    return problem;
  }
}
