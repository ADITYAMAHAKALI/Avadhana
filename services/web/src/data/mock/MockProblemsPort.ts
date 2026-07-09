import type { DiscoverFilters, ProblemsPort } from '../interfaces';
import type { Problem } from '../../types/domain';
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

  async getFeed(problemId: string) {
    return FEED_BY_PROBLEM[problemId] ?? [];
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
