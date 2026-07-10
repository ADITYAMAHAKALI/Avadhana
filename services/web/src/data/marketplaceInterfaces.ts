import type {
  AttributeMatch,
  Organization,
  OrganizationMembership,
  RFP,
  RFPMatches,
  RFPRequirement,
  RFPSearchFilters,
  Solution,
  SolutionAttribute,
  SolutionSearchFilters,
} from '../types/marketplace';

/**
 * Ports for the Solution Marketplace (issues #72/#69), split into four
 * resource-scoped ports rather than one giant `MarketplacePort` — mirrors
 * how `CurrentUserPort`/`ProblemsPort`/`ModerationPort` are already split
 * by resource in `data/interfaces.ts`. Each has a Mock and a Real
 * implementation wired through `data/index.ts`, same toggle as the rest
 * of the app (VITE_API_BASE_URL).
 */

export interface CreateOrganizationPayload {
  name: string;
}

export interface OrganizationsPort {
  create(payload: CreateOrganizationPayload): Promise<Organization>;
  listMine(): Promise<Organization[]>;
  getById(organizationId: string): Promise<Organization | null>;
  addMember(organizationId: string, userId: string, role?: 'admin' | 'member'): Promise<OrganizationMembership>;
  listMembers(organizationId: string): Promise<OrganizationMembership[]>;
}

export interface CreateRFPPayload {
  organizationId: string;
  title: string;
  description: string;
  budgetMin?: number | null;
  budgetMax?: number | null;
  timeline?: string;
  industry?: string;
  geography?: string;
  resolutionMode?: RFP['resolutionMode'];
  visibility?: RFP['visibility'];
}

export interface CreateRFPRequirementPayload {
  attributeKey: string;
  attributeValue: string;
  weight?: number;
  isHardConstraint?: boolean;
}

export interface RFPsPort {
  create(payload: CreateRFPPayload): Promise<RFP>;
  search(filters?: RFPSearchFilters): Promise<RFP[]>;
  getById(rfpId: string): Promise<RFP | null>;
  addRequirement(rfpId: string, payload: CreateRFPRequirementPayload): Promise<RFPRequirement>;
  listRequirements(rfpId: string): Promise<RFPRequirement[]>;
}

export interface CreateSolutionPayload {
  organizationId: string;
  title: string;
  description: string;
  categoryTags?: string[];
}

export interface CreateSolutionAttributePayload {
  attributeKey: string;
  attributeValue: string;
}

export interface SolutionsPort {
  create(payload: CreateSolutionPayload): Promise<Solution>;
  search(filters?: SolutionSearchFilters): Promise<Solution[]>;
  getById(solutionId: string): Promise<Solution | null>;
  addAttribute(solutionId: string, payload: CreateSolutionAttributePayload): Promise<SolutionAttribute>;
  listAttributes(solutionId: string): Promise<SolutionAttribute[]>;
}

export interface MatchingPort {
  getAttributeMatches(rfpId: string): Promise<AttributeMatch[]>;
  triggerMatchRun(rfpId: string): Promise<{ id: string; status: string; startedAt: string }>;
  getMatches(rfpId: string): Promise<RFPMatches>;
}
