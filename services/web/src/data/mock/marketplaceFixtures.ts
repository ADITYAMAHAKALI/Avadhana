import type {
  AttributeMatch,
  MatchRunTrigger,
  Organization,
  OrganizationMembership,
  RFP,
  RFPMatches,
  RFPRequirement,
  Solution,
  SolutionAttribute,
  SolutionMatch,
} from '../../types/marketplace';

/**
 * In-memory fixtures for the Marketplace mock ports — same "npm run dev
 * works with zero backend" philosophy as `data/mock/fixtures.ts`. Seeded
 * with one Organization the mock current user (`u-ravi`, see
 * `data/mock/fixtures.ts`) already belongs to, so the Marketplace screens
 * have something to render on first load without requiring the user to
 * create an org first.
 */

export const MOCK_ORG_MEMBER_USER_ID = 'u-ravi';

export const ORGANIZATIONS: Organization[] = [
  {
    id: 'org-civicworks',
    name: 'CivicWorks Foundation',
    rfpFreeQuotaUsed: 2,
    rfpFreeQuotaLimit: 100,
    billingStatus: 'active',
    createdAt: '2026-02-01T00:00:00Z',
  },
];

export const MEMBERSHIPS: OrganizationMembership[] = [
  {
    id: 'mem-1',
    organizationId: 'org-civicworks',
    userId: MOCK_ORG_MEMBER_USER_ID,
    role: 'admin',
    createdAt: '2026-02-01T00:00:00Z',
  },
];

export const SOLUTIONS: Solution[] = [
  {
    id: 'sol-aquapure',
    organizationId: 'org-vendorco',
    title: 'AquaPure Rapid Water Testing Kit',
    description: 'Field-deployable nitrate and heavy-metal testing kits with same-day lab-grade results.',
    categoryTags: ['water-quality', 'environment', 'hardware'],
    status: 'published',
    createdAt: '2026-03-01T00:00:00Z',
  },
  {
    id: 'sol-rti-assist',
    organizationId: 'org-vendorco',
    title: 'RTI Assist — Legal Filing Automation',
    description: 'Templated RTI filing and tracking software for civic organizations and legal teams.',
    categoryTags: ['legal', 'governance', 'software'],
    status: 'published',
    createdAt: '2026-03-10T00:00:00Z',
  },
  {
    id: 'sol-groundtruth',
    organizationId: 'org-dataco',
    title: 'GroundTruth Sensor Network',
    description: 'IoT groundwater sensor network with a public dashboard and alerting.',
    categoryTags: ['water-quality', 'iot', 'hardware'],
    status: 'published',
    createdAt: '2026-03-15T00:00:00Z',
  },
];

export const SOLUTION_ATTRIBUTES: Record<string, SolutionAttribute[]> = {
  'sol-aquapure': [
    { id: 'sa-1', solutionId: 'sol-aquapure', attributeKey: 'certification', attributeValue: 'ISO-17025', createdAt: '2026-03-01T00:00:00Z' },
    { id: 'sa-2', solutionId: 'sol-aquapure', attributeKey: 'turnaround_days', attributeValue: '1', createdAt: '2026-03-01T00:00:00Z' },
  ],
  'sol-groundtruth': [
    { id: 'sa-3', solutionId: 'sol-groundtruth', attributeKey: 'certification', attributeValue: 'ISO-17025', createdAt: '2026-03-15T00:00:00Z' },
    { id: 'sa-4', solutionId: 'sol-groundtruth', attributeKey: 'turnaround_days', attributeValue: '0', createdAt: '2026-03-15T00:00:00Z' },
  ],
};

export const RFPS: RFP[] = [
  {
    id: 'rfp-water-testing',
    organizationId: 'org-civicworks',
    title: 'Groundwater contamination testing — Bhopal district',
    description: 'Seeking a vendor to run rapid nitrate/heavy-metal testing across 12 wards with certified lab backing.',
    budgetMin: 200000,
    budgetMax: 800000,
    timeline: '6 weeks',
    industry: 'Environmental services',
    geography: 'Bhopal, MP',
    resolutionMode: 'marketplace',
    visibility: 'public',
    status: 'open',
    promotedProblemId: null,
    isBillable: false,
    createdAt: '2026-04-01T00:00:00Z',
  },
  {
    id: 'rfp-rti-tooling',
    organizationId: 'org-civicworks',
    title: 'RTI filing automation for 40+ active civic problems',
    description: 'Need software to templatize and track RTI filings across our committed problem workspaces.',
    budgetMin: 50000,
    budgetMax: 150000,
    timeline: '3 weeks',
    industry: 'Legal / GovTech',
    geography: 'Pan-India',
    resolutionMode: 'both',
    visibility: 'public',
    status: 'open',
    promotedProblemId: null,
    isBillable: false,
    createdAt: '2026-04-05T00:00:00Z',
  },
];

export const RFP_REQUIREMENTS: Record<string, RFPRequirement[]> = {
  'rfp-water-testing': [
    { id: 'req-1', rfpId: 'rfp-water-testing', attributeKey: 'certification', attributeValue: 'ISO-17025', weight: 2.0, isHardConstraint: true, createdAt: '2026-04-01T00:00:00Z' },
    { id: 'req-2', rfpId: 'rfp-water-testing', attributeKey: 'turnaround_days', attributeValue: '1', weight: 1.0, isHardConstraint: false, createdAt: '2026-04-01T00:00:00Z' },
  ],
};

export const ATTRIBUTE_MATCHES: Record<string, AttributeMatch[]> = {
  'rfp-water-testing': [
    {
      solution: SOLUTIONS[0],
      score: 1.0,
      matchedRequirementIds: ['req-1', 'req-2'],
    },
    {
      solution: SOLUTIONS[2],
      score: 0.67,
      matchedRequirementIds: ['req-1'],
    },
  ],
};

let nextMatchRunSeq = 1;
export const MATCH_RUNS_BY_RFP: Record<string, MatchRunTrigger> = {};
export const SOLUTION_MATCHES_BY_RFP: Record<string, SolutionMatch[]> = {};

/** Mock counterpart to the backend's async job — resolves "instantly" (no queue) since there's no worker to poll here. */
export function mockTriggerMatchRun(rfpId: string): MatchRunTrigger {
  const run: MatchRunTrigger = {
    id: `run-${nextMatchRunSeq++}`,
    rfpId,
    status: 'completed',
    startedAt: new Date().toISOString(),
  };
  MATCH_RUNS_BY_RFP[rfpId] = run;
  SOLUTION_MATCHES_BY_RFP[rfpId] = [
    {
      id: `sm-${run.id}-1`,
      matchRunId: run.id,
      solution: SOLUTIONS[0],
      finalRrfScore: 0.031,
      rank: 1,
      signalScores: { attribute_match: 1.0, summary: 0.82, technical_spec: 0.71 },
      signalRanks: { attribute_match: 1, summary: 1, technical_spec: 2 },
    },
    {
      id: `sm-${run.id}-2`,
      matchRunId: run.id,
      solution: SOLUTIONS[2],
      finalRrfScore: 0.027,
      rank: 2,
      signalScores: { attribute_match: 0.67, summary: 0.74, technical_spec: 0.79 },
      signalRanks: { attribute_match: 2, summary: 2, technical_spec: 1 },
    },
  ];
  return run;
}

export function mockGetMatches(rfpId: string): RFPMatches {
  return {
    matchRun: MATCH_RUNS_BY_RFP[rfpId] ?? null,
    matches: SOLUTION_MATCHES_BY_RFP[rfpId] ?? [],
  };
}
