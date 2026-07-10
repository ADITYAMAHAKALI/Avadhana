import type { CreateOrganizationPayload, OrganizationsPort } from '../marketplaceInterfaces';
import type { Organization, OrganizationMembership } from '../../types/marketplace';
import { MEMBERSHIPS, MOCK_ORG_MEMBER_USER_ID, ORGANIZATIONS } from './marketplaceFixtures';

let nextOrgId = 1;
let nextMembershipId = 1;

export class MockOrganizationsPort implements OrganizationsPort {
  async create(payload: CreateOrganizationPayload): Promise<Organization> {
    const organization: Organization = {
      id: `mock-org-${nextOrgId++}`,
      name: payload.name,
      rfpFreeQuotaUsed: 0,
      rfpFreeQuotaLimit: 100,
      billingStatus: 'active',
      createdAt: new Date().toISOString(),
    };
    ORGANIZATIONS.unshift(organization);
    MEMBERSHIPS.unshift({
      id: `mock-mem-${nextMembershipId++}`,
      organizationId: organization.id,
      userId: MOCK_ORG_MEMBER_USER_ID,
      role: 'admin',
      createdAt: organization.createdAt,
    });
    return organization;
  }

  async listMine(): Promise<Organization[]> {
    const myOrgIds = new Set(
      MEMBERSHIPS.filter((m) => m.userId === MOCK_ORG_MEMBER_USER_ID).map((m) => m.organizationId),
    );
    return ORGANIZATIONS.filter((o) => myOrgIds.has(o.id));
  }

  async getById(organizationId: string): Promise<Organization | null> {
    return ORGANIZATIONS.find((o) => o.id === organizationId) ?? null;
  }

  async addMember(
    organizationId: string,
    userId: string,
    role: 'admin' | 'member' = 'member',
  ): Promise<OrganizationMembership> {
    const membership: OrganizationMembership = {
      id: `mock-mem-${nextMembershipId++}`,
      organizationId,
      userId,
      role,
      createdAt: new Date().toISOString(),
    };
    MEMBERSHIPS.push(membership);
    return membership;
  }

  async listMembers(organizationId: string): Promise<OrganizationMembership[]> {
    return MEMBERSHIPS.filter((m) => m.organizationId === organizationId);
  }
}
