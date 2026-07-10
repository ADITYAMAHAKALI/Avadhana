import type { MatchingPort } from '../marketplaceInterfaces';
import type { AttributeMatch, MatchRunTrigger, RFPMatches } from '../../types/marketplace';
import { ATTRIBUTE_MATCHES, mockGetMatches, mockTriggerMatchRun } from './marketplaceFixtures';

export class MockMatchingPort implements MatchingPort {
  async getAttributeMatches(rfpId: string): Promise<AttributeMatch[]> {
    return ATTRIBUTE_MATCHES[rfpId] ?? [];
  }

  async triggerMatchRun(rfpId: string): Promise<MatchRunTrigger> {
    return mockTriggerMatchRun(rfpId);
  }

  async getMatches(rfpId: string): Promise<RFPMatches> {
    return mockGetMatches(rfpId);
  }
}
