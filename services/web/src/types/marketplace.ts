/**
 * Solution Marketplace domain types — mirrors
 * `services/backend-api/app/schemas_marketplace.py` field-for-field
 * (camelCase on the wire, same as `types/domain.ts`'s civic-Problem
 * types mirror `app/schemas.py`). See CLAUDE.md "Solution Marketplace
 * Architecture" for the full domain model this implements.
 */

export type OrganizationRole = 'admin' | 'member';
export type ResolutionMode = 'community' | 'marketplace' | 'both';
export type RFPVisibility = 'public' | 'invite_only';
export type RFPStatus = 'draft' | 'open' | 'closed';
export type SolutionStatus = 'draft' | 'published';
export type BillingEventType = 'free_rfp_posted' | 'billable_rfp_posted';
export type MatchRunStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Organization {
  id: string;
  name: string;
  rfpFreeQuotaUsed: number;
  rfpFreeQuotaLimit: number;
  billingStatus: string;
  createdAt: string;
}

export interface OrganizationMembership {
  id: string;
  organizationId: string;
  userId: string;
  role: OrganizationRole;
  createdAt: string;
}

export interface RFPRequirement {
  id: string;
  rfpId: string;
  attributeKey: string;
  attributeValue: string;
  weight: number;
  isHardConstraint: boolean;
  createdAt: string;
}

export interface RFP {
  id: string;
  organizationId: string;
  title: string;
  description: string;
  budgetMin: number | null;
  budgetMax: number | null;
  timeline: string;
  industry: string;
  geography: string;
  resolutionMode: ResolutionMode;
  visibility: RFPVisibility;
  status: RFPStatus;
  promotedProblemId: string | null;
  isBillable: boolean;
  createdAt: string;
}

export interface SolutionAttribute {
  id: string;
  solutionId: string;
  attributeKey: string;
  attributeValue: string;
  createdAt: string;
}

export interface Solution {
  id: string;
  organizationId: string;
  title: string;
  description: string;
  categoryTags: string[];
  status: SolutionStatus;
  createdAt: string;
}

export interface BillingEvent {
  id: string;
  organizationId: string;
  rfpId: string | null;
  eventType: BillingEventType;
  amount: number | null;
  occurredAt: string;
}

/** `GET /marketplace/rfps/{rfpId}/attribute-matches` item — issue #66, no ML. */
export interface AttributeMatch {
  solution: Solution;
  score: number;
  matchedRequirementIds: string[];
}

/** `POST /marketplace/rfps/{rfpId}/matches/trigger` response — the newly-created MatchRun row. */
export interface MatchRunTrigger {
  id: string;
  rfpId: string;
  status: MatchRunStatus;
  startedAt: string;
}

/** One ranked Solution from a completed MatchRun, with full per-signal explainability breakdown. */
export interface SolutionMatch {
  id: string;
  matchRunId: string;
  solution: Solution;
  finalRrfScore: number;
  rank: number;
  signalScores: Record<string, number>;
  signalRanks: Record<string, number>;
}

/** `GET /marketplace/rfps/{rfpId}/matches` response — null matchRun means no run has completed yet. */
export interface RFPMatches {
  matchRun: MatchRunTrigger | null;
  matches: SolutionMatch[];
}

export interface RFPSearchFilters {
  industry?: string;
  geography?: string;
  resolutionMode?: ResolutionMode;
}

export interface SolutionSearchFilters {
  categoryTag?: string;
  organizationId?: string;
}
