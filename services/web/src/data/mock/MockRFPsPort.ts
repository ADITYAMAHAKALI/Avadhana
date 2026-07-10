import type { CreateRFPPayload, CreateRFPRequirementPayload, RFPsPort } from '../marketplaceInterfaces';
import type { RFP, RFPRequirement, RFPSearchFilters } from '../../types/marketplace';
import { RFPS, RFP_REQUIREMENTS } from './marketplaceFixtures';

let nextRfpId = 1;
let nextRequirementId = 1;

export class MockRFPsPort implements RFPsPort {
  async create(payload: CreateRFPPayload): Promise<RFP> {
    const rfp: RFP = {
      id: `mock-rfp-${nextRfpId++}`,
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
      status: 'open',
      promotedProblemId: null,
      isBillable: false,
      createdAt: new Date().toISOString(),
    };
    RFPS.unshift(rfp);
    RFP_REQUIREMENTS[rfp.id] = [];
    return rfp;
  }

  async search(filters: RFPSearchFilters = {}): Promise<RFP[]> {
    return RFPS.filter((r) => {
      if (filters.industry && !r.industry.toLowerCase().includes(filters.industry.toLowerCase())) return false;
      if (filters.geography && !r.geography.toLowerCase().includes(filters.geography.toLowerCase())) return false;
      if (filters.resolutionMode && r.resolutionMode !== filters.resolutionMode) return false;
      return true;
    });
  }

  async getById(rfpId: string): Promise<RFP | null> {
    return RFPS.find((r) => r.id === rfpId) ?? null;
  }

  async addRequirement(rfpId: string, payload: CreateRFPRequirementPayload): Promise<RFPRequirement> {
    const requirement: RFPRequirement = {
      id: `mock-req-${nextRequirementId++}`,
      rfpId,
      attributeKey: payload.attributeKey,
      attributeValue: payload.attributeValue,
      weight: payload.weight ?? 1.0,
      isHardConstraint: payload.isHardConstraint ?? false,
      createdAt: new Date().toISOString(),
    };
    RFP_REQUIREMENTS[rfpId] = [...(RFP_REQUIREMENTS[rfpId] ?? []), requirement];
    return requirement;
  }

  async listRequirements(rfpId: string): Promise<RFPRequirement[]> {
    return RFP_REQUIREMENTS[rfpId] ?? [];
  }
}
