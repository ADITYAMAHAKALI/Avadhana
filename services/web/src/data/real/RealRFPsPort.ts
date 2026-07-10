import type { CreateRFPPayload, CreateRFPRequirementPayload, RFPsPort } from '../marketplaceInterfaces';
import type { RFP, RFPRequirement, RFPSearchFilters } from '../../types/marketplace';
import { apiFetch, ApiError } from './httpClient';

/**
 * Real HTTP port for `app/routers/marketplace/rfps.py`. Reads (search/get
 * requirements) work logged-out (`auth: false`) mirroring that router's
 * "discovery is public except invite-only" rule; writes (create RFP, add
 * requirement) require auth and member-of-org on the backend.
 */
export class RealRFPsPort implements RFPsPort {
  async create(payload: CreateRFPPayload): Promise<RFP> {
    return apiFetch<RFP>('/marketplace/rfps', {
      method: 'POST',
      body: {
        organizationId: payload.organizationId,
        title: payload.title,
        description: payload.description,
        budgetMin: payload.budgetMin ?? null,
        budgetMax: payload.budgetMax ?? null,
        timeline: payload.timeline ?? '',
        industry: payload.industry ?? '',
        geography: payload.geography ?? '',
        resolutionMode: payload.resolutionMode ?? 'marketplace',
        visibility: payload.visibility ?? 'public',
      },
    });
  }

  async search(filters: RFPSearchFilters = {}): Promise<RFP[]> {
    const params = new URLSearchParams();
    if (filters.industry) params.set('industry', filters.industry);
    if (filters.geography) params.set('geography', filters.geography);
    if (filters.resolutionMode) params.set('resolutionMode', filters.resolutionMode);
    const qs = params.toString();
    return apiFetch<RFP[]>(`/marketplace/rfps${qs ? `?${qs}` : ''}`, { auth: false });
  }

  async getById(rfpId: string): Promise<RFP | null> {
    try {
      return await apiFetch<RFP>(`/marketplace/rfps/${rfpId}`, { auth: false });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  }

  async addRequirement(rfpId: string, payload: CreateRFPRequirementPayload): Promise<RFPRequirement> {
    return apiFetch<RFPRequirement>(`/marketplace/rfps/${rfpId}/requirements`, {
      method: 'POST',
      body: {
        attributeKey: payload.attributeKey,
        attributeValue: payload.attributeValue,
        weight: payload.weight ?? 1.0,
        isHardConstraint: payload.isHardConstraint ?? false,
      },
    });
  }

  async listRequirements(rfpId: string): Promise<RFPRequirement[]> {
    return apiFetch<RFPRequirement[]>(`/marketplace/rfps/${rfpId}/requirements`, { auth: false });
  }
}
