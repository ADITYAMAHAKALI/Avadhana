import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { organizationsPort } from '../data';
import type { Organization } from '../types/marketplace';

const ACTIVE_ORG_STORAGE_KEY = 'avadhana_active_org_id';

/**
 * Tracks "which Organization is the signed-in user currently acting as"
 * across the Marketplace screens — every RFP/Solution create call needs
 * an `organizationId`, and a user can belong to more than one
 * Organization (see `OrganizationMembership`), so this can't just be
 * inferred from the current user the way civic Problem actions can.
 *
 * Modeled as its own context (not folded into AuthContext) because it's
 * scoped to the Marketplace surface only and depends on a fetch
 * (`organizationsPort.listMine()`) rather than being known at login time.
 * Mirrors AuthContext's shape (localStorage-backed selection + a
 * provider/hook pair) for consistency, but stays independent so civic
 * screens never need to know it exists.
 */
interface OrganizationContextValue {
  /** All Organizations the current user belongs to. Empty until loaded. */
  organizations: Organization[];
  /** The Organization the user is currently acting as, or null if they belong to none yet. */
  activeOrganization: Organization | null;
  isLoading: boolean;
  setActiveOrganizationId: (organizationId: string) => void;
  /** Re-fetch the caller's Organizations — call after creating a new one. */
  refresh: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextValue | null>(null);

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrganizationId, setActiveOrganizationIdState] = useState<string | null>(() =>
    localStorage.getItem(ACTIVE_ORG_STORAGE_KEY),
  );
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const orgs = await organizationsPort.listMine();
      setOrganizations(orgs);
      setActiveOrganizationIdState((current) => {
        if (current && orgs.some((o) => o.id === current)) return current;
        const fallback = orgs[0]?.id ?? null;
        if (fallback) localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, fallback);
        return fallback;
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => setIsLoading(false));
  }, [refresh]);

  const setActiveOrganizationId = useCallback((organizationId: string) => {
    localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, organizationId);
    setActiveOrganizationIdState(organizationId);
  }, []);

  const activeOrganization = useMemo(
    () => organizations.find((o) => o.id === activeOrganizationId) ?? null,
    [organizations, activeOrganizationId],
  );

  const value = useMemo<OrganizationContextValue>(
    () => ({ organizations, activeOrganization, isLoading, setActiveOrganizationId, refresh }),
    [organizations, activeOrganization, isLoading, setActiveOrganizationId, refresh],
  );

  return <OrganizationContext value={value}>{children}</OrganizationContext>;
}

export function useOrganization() {
  const ctx = useContext(OrganizationContext);
  if (!ctx) throw new Error('useOrganization must be used within OrganizationProvider');
  return ctx;
}
