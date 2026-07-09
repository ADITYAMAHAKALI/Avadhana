import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { problemsPort } from '../data';
import type { DiscoverFilters } from '../data/interfaces';
import type { Problem, Tier } from '../types/domain';
import { PageHeader } from '../components/shared/PageHeader';
import { TierChip } from '../components/shared/TierChip';
import { Button } from '../components/shared/Button';
import styles from './DiscoverPage.module.css';

const TIERS: Tier[] = ['S', 'A', 'B', 'C', 'D'];

function pluralize(count: number, singular: string): string {
  return count === 1 ? singular : `${singular}s`;
}

export function DiscoverPage() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [query, setQuery] = useState('');
  const [activeTier, setActiveTier] = useState<Tier | null>(null);
  const [location, setLocation] = useState('');
  const [category, setCategory] = useState('');

  useEffect(() => {
    const filters: DiscoverFilters = {
      q: query.trim() || undefined,
      tier: activeTier ?? undefined,
      location: location.trim() || undefined,
      category: category.trim() || undefined,
    };
    // Small debounce so free-text fields (query/location/category) don't
    // fire a request on every keystroke; tier clicks resolve immediately
    // on the next tick regardless since the timer is short.
    const handle = setTimeout(() => {
      problemsPort.listDiscoverable(filters).then(setProblems);
    }, 250);
    return () => clearTimeout(handle);
  }, [query, activeTier, location, category]);

  const hasActiveFilters = Boolean(activeTier || location.trim() || category.trim());

  function clearFilters() {
    setActiveTier(null);
    setLocation('');
    setCategory('');
  }

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Deliberate discovery — no algorithm"
        title="Find a problem worth 90 days"
        actions={
          <Link to="/problems/new" style={{ textDecoration: 'none' }}>
            <Button variant="primary">+ Propose a problem</Button>
          </Link>
        }
      />

      <div className={styles.searchRow}>
        <div className={styles.searchBar}>
          <span className={styles.searchIcon}>⌕</span>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Search by topic, place, or keyword…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className={styles.tierButtons}>
          {TIERS.map((tier) => (
            <button
              key={tier}
              type="button"
              className={`${styles.tierButton} ${activeTier === tier ? styles.tierButtonActive : ''}`}
              onClick={() => setActiveTier(activeTier === tier ? null : tier)}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.filterRow}>
        <span className={styles.filterLabel}>Filter:</span>
        <input
          className={styles.filterInput}
          type="text"
          placeholder="📍 Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />
        <input
          className={styles.filterInput}
          type="text"
          placeholder="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
        {hasActiveFilters && (
          <button type="button" className={styles.clearFilters} onClick={clearFilters}>
            Clear filters ×
          </button>
        )}
      </div>

      <div className={styles.grid}>
        {problems.map((problem) => (
          <Link to={`/problems/${problem.id}`} key={problem.id} className={styles.card}>
            <div className={styles.cardTop}>
              <TierChip tier={problem.tier} />
              <span className={styles.cardLocation}>
                {problem.location} · {problem.category}
              </span>
            </div>
            <div className={styles.cardTitle}>{problem.title}</div>
            <div className={styles.cardSummary}>{problem.summary}</div>
            <div className={styles.cardFooter}>
              <span>
                <span className={styles.countThinker}>{problem.thinkerCount}</span> {pluralize(problem.thinkerCount, 'thinker')}
              </span>
              <span>
                <span className={styles.countActor}>{problem.actorCount}</span> {pluralize(problem.actorCount, 'actor')}
              </span>
              <span>
                <span className={styles.countBacker}>{problem.backerCount}</span> {pluralize(problem.backerCount, 'backer')}
              </span>
              <span className={styles.following}>↗ {problem.followingCount} following</span>
            </div>
          </Link>
        ))}
        {problems.length === 0 && (
          <div className={styles.empty}>No problems match these filters yet. Try widening your search, or propose one.</div>
        )}
      </div>
    </div>
  );
}
