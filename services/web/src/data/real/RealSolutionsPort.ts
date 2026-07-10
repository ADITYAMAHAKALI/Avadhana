import type { CreateSolutionAttributePayload, CreateSolutionPayload, SolutionsPort } from '../marketplaceInterfaces';
import type { Solution, SolutionAttribute, SolutionSearchFilters } from '../../types/marketplace';
import { apiFetch, ApiError } from './httpClient';

/**
 * Real HTTP port for `app/routers/marketplace/solutions.py`. Reads are
 * fully public (no invite-only concept for Solutions — see that router's
 * docstring); publishing/attribute-adding requires auth + member-of-org.
 */
export class RealSolutionsPort implements SolutionsPort {
  async create(payload: CreateSolutionPayload): Promise<Solution> {
    return apiFetch<Solution>('/marketplace/solutions', {
      method: 'POST',
      body: {
        organizationId: payload.organizationId,
        title: payload.title,
        description: payload.description,
        categoryTags: payload.categoryTags ?? [],
      },
    });
  }

  async search(filters: SolutionSearchFilters = {}): Promise<Solution[]> {
    const params = new URLSearchParams();
    if (filters.categoryTag) params.set('categoryTag', filters.categoryTag);
    if (filters.organizationId) params.set('organizationId', filters.organizationId);
    const qs = params.toString();
    return apiFetch<Solution[]>(`/marketplace/solutions${qs ? `?${qs}` : ''}`, { auth: false });
  }

  async getById(solutionId: string): Promise<Solution | null> {
    try {
      return await apiFetch<Solution>(`/marketplace/solutions/${solutionId}`, { auth: false });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  }

  async addAttribute(solutionId: string, payload: CreateSolutionAttributePayload): Promise<SolutionAttribute> {
    return apiFetch<SolutionAttribute>(`/marketplace/solutions/${solutionId}/attributes`, {
      method: 'POST',
      body: payload,
    });
  }

  async listAttributes(solutionId: string): Promise<SolutionAttribute[]> {
    return apiFetch<SolutionAttribute[]>(`/marketplace/solutions/${solutionId}/attributes`, { auth: false });
  }
}
