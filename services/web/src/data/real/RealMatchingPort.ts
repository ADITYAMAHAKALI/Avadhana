import type { MatchingPort } from '../marketplaceInterfaces';
import type { AttributeMatch, MatchRunTrigger, RFPMatches } from '../../types/marketplace';
import { apiFetch } from './httpClient';

/**
 * Real HTTP port for `app/routers/marketplace/matching.py` (attribute
 * matches, issue #66) and `app/routers/marketplace/matches.py` (RRF
 * trigger + poll, issue #68). Both read endpoints work logged-out for a
 * public RFP (mirroring `GET /marketplace/rfps/{id}` itself); triggering
 * a run requires auth + member-of-the-posting-org on the backend.
 */
export class RealMatchingPort implements MatchingPort {
  async getAttributeMatches(rfpId: string): Promise<AttributeMatch[]> {
    return apiFetch<AttributeMatch[]>(`/marketplace/rfps/${rfpId}/attribute-matches`, { auth: false });
  }

  async triggerMatchRun(rfpId: string): Promise<MatchRunTrigger> {
    return apiFetch<MatchRunTrigger>(`/marketplace/rfps/${rfpId}/matches/trigger`, { method: 'POST' });
  }

  async getMatches(rfpId: string): Promise<RFPMatches> {
    return apiFetch<RFPMatches>(`/marketplace/rfps/${rfpId}/matches`, { auth: false });
  }
}
