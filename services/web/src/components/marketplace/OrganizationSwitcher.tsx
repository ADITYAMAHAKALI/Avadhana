import { useState, type FormEvent } from 'react';
import { useOrganization } from '../../context/OrganizationContext';
import { organizationsPort } from '../../data';
import { ApiError } from '../../data/real/httpClient';
import styles from './OrganizationSwitcher.module.css';

/**
 * The entry point every Marketplace screen needs: which Organization is
 * the signed-in user currently acting as (see OrganizationContext's
 * docstring for why this can't be inferred from the civic User alone).
 * Shows a select to switch between the caller's existing Organizations,
 * plus an inline "create one" form when they have none yet — you can't
 * post an RFP or Solution without an Organization, so this is the first
 * thing a first-time Marketplace visitor needs to do.
 */
export function OrganizationSwitcher() {
  const { organizations, activeOrganization, isLoading, setActiveOrganizationId, refresh } = useOrganization();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [name, setName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const org = await organizationsPort.create({ name: name.trim() });
      await refresh();
      setActiveOrganizationId(org.id);
      setName('');
      setShowCreateForm(false);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not create this Organization. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <div className={styles.bar}>Loading your Organizations…</div>;
  }

  return (
    <div className={styles.bar}>
      {organizations.length > 0 && (
        <div className={styles.switcherRow}>
          <span className={styles.label}>Acting as</span>
          <select
            className={styles.select}
            value={activeOrganization?.id ?? ''}
            onChange={(e) => setActiveOrganizationId(e.target.value)}
          >
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
          {activeOrganization && (
            <span className={styles.quota}>
              {activeOrganization.rfpFreeQuotaUsed} / {activeOrganization.rfpFreeQuotaLimit} free RFPs used
            </span>
          )}
          <button type="button" className={styles.newOrgLink} onClick={() => setShowCreateForm((v) => !v)}>
            + New Organization
          </button>
        </div>
      )}

      {organizations.length === 0 && !showCreateForm && (
        <div className={styles.emptyRow}>
          <span>You don&apos;t belong to an Organization yet. Create one to post an RFP or publish a Solution.</span>
          <button type="button" className={styles.newOrgLink} onClick={() => setShowCreateForm(true)}>
            + Create Organization
          </button>
        </div>
      )}

      {showCreateForm && (
        <form className={styles.createForm} onSubmit={handleCreate}>
          <input
            className={styles.input}
            type="text"
            placeholder="Organization name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={300}
            required
          />
          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? 'Creating…' : 'Create'}
          </button>
          {organizations.length > 0 && (
            <button type="button" className={styles.cancelButton} onClick={() => setShowCreateForm(false)}>
              Cancel
            </button>
          )}
        </form>
      )}

      {error && <div className={styles.error}>{error}</div>}
    </div>
  );
}
