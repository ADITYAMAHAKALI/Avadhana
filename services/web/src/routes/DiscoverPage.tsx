import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { problemsPort } from '../data';
import type { Problem, Tier } from '../types/domain';
import { PageHeader } from '../components/shared/PageHeader';
import { TierChip } from '../components/shared/TierChip';
import styles from './DiscoverPage.module.css';

const TIERS: Tier[] = ['S', 'A', 'B', 'C', 'D'];

function pluralize(count: number, singular: string): string {
  return count === 1 ? singular : `${singular}s`;
}

export function DiscoverPage() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [activeTier, setActiveTier] = useState<Tier>('S');

  useEffect(() => {
    problemsPort.listDiscoverable().then(setProblems);
  }, []);

  return (
    <div className={styles.page}>
      <PageHeader eyebrow="Deliberate discovery — no algorithm" title="Find a problem worth 90 days" />

      <div className={styles.searchRow}>
        <div className={styles.searchBar}>
          <span className={styles.searchIcon}>⌕</span>
          <span className={styles.searchPlaceholder}>Search by topic, place, or keyword…</span>
        </div>
        <div className={styles.tierButtons}>
          {TIERS.map((tier) => (
            <button
              key={tier}
              type="button"
              className={`${styles.tierButton} ${activeTier === tier ? styles.tierButtonActive : ''}`}
              onClick={() => setActiveTier(tier)}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.filterRow}>
        <span className={styles.filterLabel}>Filter:</span>
        <span className={styles.filterChip}>📍 Maharashtra</span>
        <span className={styles.filterChip}>Needs: Actors</span>
        <span className={styles.sortLabel}>Sort: Fewest committed →</span>
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
      </div>
    </div>
  );
}
