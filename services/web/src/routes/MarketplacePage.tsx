import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { rfpsPort, solutionsPort } from '../data';
import { useOrganization } from '../context/OrganizationContext';
import type { RFP, RFPSearchFilters, ResolutionMode } from '../types/marketplace';
import type { Solution, SolutionSearchFilters } from '../types/marketplace';
import { PageHeader } from '../components/shared/PageHeader';
import { Button } from '../components/shared/Button';
import { OrganizationSwitcher } from '../components/marketplace/OrganizationSwitcher';
import styles from './MarketplacePage.module.css';

type Tab = 'rfps' | 'solutions';

const RESOLUTION_MODES: ResolutionMode[] = ['community', 'marketplace', 'both'];

function money(value: number | null): string {
  if (value === null) return '—';
  return `₹${value.toLocaleString('en-IN')}`;
}

export function MarketplacePage() {
  const { activeOrganization, organizations, isLoading: orgsLoading } = useOrganization();
  const [tab, setTab] = useState<Tab>('rfps');

  const [rfps, setRfps] = useState<RFP[]>([]);
  const [industry, setIndustry] = useState('');
  const [geography, setGeography] = useState('');
  const [resolutionMode, setResolutionMode] = useState<ResolutionMode | ''>('');

  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [categoryTag, setCategoryTag] = useState('');

  useEffect(() => {
    if (tab !== 'rfps') return;
    const filters: RFPSearchFilters = {
      industry: industry.trim() || undefined,
      geography: geography.trim() || undefined,
      resolutionMode: resolutionMode || undefined,
    };
    const handle = setTimeout(() => {
      rfpsPort.search(filters).then(setRfps);
    }, 250);
    return () => clearTimeout(handle);
  }, [tab, industry, geography, resolutionMode]);

  useEffect(() => {
    if (tab !== 'solutions') return;
    const filters: SolutionSearchFilters = { categoryTag: categoryTag.trim() || undefined };
    const handle = setTimeout(() => {
      solutionsPort.search(filters).then(setSolutions);
    }, 250);
    return () => clearTimeout(handle);
  }, [tab, categoryTag]);

  const hasOrg = Boolean(activeOrganization);
  const gateTitle = orgsLoading
    ? undefined
    : hasOrg
      ? undefined
      : organizations.length === 0
        ? 'Create an Organization first — see the switcher above.'
        : undefined;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="B2B / B2G — independent of the 3-slot civic mechanic"
        title="Marketplace"
        subtitle="RFPs from buyers, Solutions from providers, matched by structured attributes and semantic similarity. Posting an RFP or publishing a Solution never spends a focus slot and is never locked for 90 days."
        actions={
          <div className={styles.headerActions}>
            {tab === 'rfps' ? (
              <Link to="/marketplace/rfps/new" style={{ textDecoration: 'none' }} title={gateTitle}>
                <Button variant="primary" disabled={!hasOrg}>
                  + Post an RFP
                </Button>
              </Link>
            ) : (
              <Link to="/marketplace/solutions/new" style={{ textDecoration: 'none' }} title={gateTitle}>
                <Button variant="primary" disabled={!hasOrg}>
                  + Publish a Solution
                </Button>
              </Link>
            )}
          </div>
        }
      />

      <OrganizationSwitcher />

      <div className={styles.tabs}>
        <button
          type="button"
          className={`${styles.tab} ${tab === 'rfps' ? styles.tabActive : ''}`}
          onClick={() => setTab('rfps')}
        >
          RFPs
        </button>
        <button
          type="button"
          className={`${styles.tab} ${tab === 'solutions' ? styles.tabActive : ''}`}
          onClick={() => setTab('solutions')}
        >
          Solutions
        </button>
      </div>

      {tab === 'rfps' && (
        <>
          <div className={styles.filterRow}>
            <input
              className={styles.filterInput}
              type="text"
              placeholder="Industry"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
            />
            <input
              className={styles.filterInput}
              type="text"
              placeholder="Geography"
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
            />
            <select
              className={styles.filterSelect}
              value={resolutionMode}
              onChange={(e) => setResolutionMode(e.target.value as ResolutionMode | '')}
            >
              <option value="">Any resolution mode</option>
              {RESOLUTION_MODES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.grid}>
            {rfps.map((rfp) => (
              <Link to={`/marketplace/rfps/${rfp.id}`} key={rfp.id} className={styles.card}>
                <div className={styles.cardTop}>
                  <span className={styles.modeBadge}>{rfp.resolutionMode}</span>
                  <span className={styles.cardMeta}>
                    {rfp.industry || 'Any industry'} · {rfp.geography || 'Any geography'}
                  </span>
                </div>
                <div className={styles.cardTitle}>{rfp.title}</div>
                <div className={styles.cardSummary}>{rfp.description}</div>
                <div className={styles.cardFooter}>
                  <span>
                    {money(rfp.budgetMin)} – {money(rfp.budgetMax)}
                  </span>
                  <span>{rfp.timeline || 'No timeline given'}</span>
                  <span className={styles.statusBadge}>{rfp.status}</span>
                </div>
              </Link>
            ))}
            {rfps.length === 0 && <div className={styles.empty}>No RFPs match these filters yet.</div>}
          </div>
        </>
      )}

      {tab === 'solutions' && (
        <>
          <div className={styles.filterRow}>
            <input
              className={styles.filterInput}
              type="text"
              placeholder="Category tag"
              value={categoryTag}
              onChange={(e) => setCategoryTag(e.target.value)}
            />
          </div>

          <div className={styles.grid}>
            {solutions.map((solution) => (
              <div className={styles.card} key={solution.id}>
                <div className={styles.cardTop}>
                  <span className={styles.statusBadge}>{solution.status}</span>
                </div>
                <div className={styles.cardTitle}>{solution.title}</div>
                <div className={styles.cardSummary}>{solution.description}</div>
                <div className={styles.tagRow}>
                  {solution.categoryTags.map((tag) => (
                    <span className={styles.tag} key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {solutions.length === 0 && <div className={styles.empty}>No Solutions match these filters yet.</div>}
          </div>
        </>
      )}
    </div>
  );
}
