import type { ProblemsPort } from '../interfaces';
import {
  FEED_BY_PROBLEM,
  GRAPH_BY_PROBLEM,
  PROBLEMS,
  TASKS_BY_PROBLEM,
} from './fixtures';

export class MockProblemsPort implements ProblemsPort {
  async listDiscoverable() {
    return PROBLEMS;
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
}
