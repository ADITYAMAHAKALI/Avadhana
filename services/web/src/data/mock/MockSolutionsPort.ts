import type { CreateSolutionAttributePayload, CreateSolutionPayload, SolutionsPort } from '../marketplaceInterfaces';
import type { Solution, SolutionAttribute, SolutionSearchFilters } from '../../types/marketplace';
import { SOLUTIONS, SOLUTION_ATTRIBUTES } from './marketplaceFixtures';

let nextSolutionId = 1;
let nextAttributeId = 1;

export class MockSolutionsPort implements SolutionsPort {
  async create(payload: CreateSolutionPayload): Promise<Solution> {
    const solution: Solution = {
      id: `mock-sol-${nextSolutionId++}`,
      organizationId: payload.organizationId,
      title: payload.title,
      description: payload.description,
      categoryTags: payload.categoryTags ?? [],
      status: 'published',
      createdAt: new Date().toISOString(),
    };
    SOLUTIONS.unshift(solution);
    SOLUTION_ATTRIBUTES[solution.id] = [];
    return solution;
  }

  async search(filters: SolutionSearchFilters = {}): Promise<Solution[]> {
    return SOLUTIONS.filter((s) => {
      if (filters.categoryTag && !s.categoryTags.includes(filters.categoryTag)) return false;
      if (filters.organizationId && s.organizationId !== filters.organizationId) return false;
      return true;
    });
  }

  async getById(solutionId: string): Promise<Solution | null> {
    return SOLUTIONS.find((s) => s.id === solutionId) ?? null;
  }

  async addAttribute(solutionId: string, payload: CreateSolutionAttributePayload): Promise<SolutionAttribute> {
    const attribute: SolutionAttribute = {
      id: `mock-sa-${nextAttributeId++}`,
      solutionId,
      attributeKey: payload.attributeKey,
      attributeValue: payload.attributeValue,
      createdAt: new Date().toISOString(),
    };
    SOLUTION_ATTRIBUTES[solutionId] = [...(SOLUTION_ATTRIBUTES[solutionId] ?? []), attribute];
    return attribute;
  }

  async listAttributes(solutionId: string): Promise<SolutionAttribute[]> {
    return SOLUTION_ATTRIBUTES[solutionId] ?? [];
  }
}
