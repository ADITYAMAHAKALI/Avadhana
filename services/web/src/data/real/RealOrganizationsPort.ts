import type { CreateOrganizationPayload, OrganizationsPort } from '../marketplaceInterfaces';
import type { Organization, OrganizationMembership } from '../../types/marketplace';
import { apiFetch, ApiError } from './httpClient';

/**
 * Real HTTP port for `app/routers/marketplace/organizations.py`. Every
 * route there requires auth (no anonymous "discovery is public" carve-out
 * like civic Problems get — see that router's module docstring), so
 * every call here goes through apiFetch's default `auth: true`.
 */
export class RealOrganizationsPort implements OrganizationsPort {
  async create(payload: CreateOrganizationPayload): Promise<Organization> {
    return apiFetch<Organization>('/marketplace/organizations', { method: 'POST', body: payload });
  }

  async listMine(): Promise<Organization[]> {
    return apiFetch<Organization[]>('/marketplace/organizations/mine');
  }

  async getById(organizationId: string): Promise<Organization | null> {
    try {
      return await apiFetch<Organization>(`/marketplace/organizations/${organizationId}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  }

  async addMember(
    organizationId: string,
    userId: string,
    role: 'admin' | 'member' = 'member',
  ): Promise<OrganizationMembership> {
    return apiFetch<OrganizationMembership>(`/marketplace/organizations/${organizationId}/members`, {
      method: 'POST',
      body: { userId, role },
    });
  }

  async listMembers(organizationId: string): Promise<OrganizationMembership[]> {
    return apiFetch<OrganizationMembership[]>(`/marketplace/organizations/${organizationId}/members`);
  }
}
