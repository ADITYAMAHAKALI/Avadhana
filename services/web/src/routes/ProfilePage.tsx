import { useEffect, useState } from 'react';
import { currentUserPort, problemsPort } from '../data';
import type { CommitmentHistoryEntry, CommittedProblemSummary, Problem, User } from '../types/domain';
import { RoleChip } from '../components/shared/RoleChip';
import { TierChip } from '../components/shared/TierChip';
import styles from './ProfilePage.module.css';

interface CommittedCard {
  summary: CommittedProblemSummary;
  problem: Problem;
}

const STATUS_LABEL: Record<CommitmentHistoryEntry['status'], string> = {
  active: 'Active',
  resolved: 'Resolved',
  continued: 'Continued',
  abandoned: 'Abandoned',
};

export function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [cards, setCards] = useState<CommittedCard[]>([]);
  const [history, setHistory] = useState<CommitmentHistoryEntry[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [currentUser, committed, commitmentHistory] = await Promise.all([
        currentUserPort.getCurrentUser(),
        currentUserPort.getCommittedProblems(),
        currentUserPort.getCommitmentHistory(),
      ]);
      const joined = await Promise.all(
        committed.map(async (summary) => {
          const problem = await problemsPort.getById(summary.problemId);
          return problem ? { summary, problem } : null;
        }),
      );
      if (!cancelled) {
        setUser(currentUser);
        setCards(joined.filter((c): c is CommittedCard => c !== null));
        setHistory(commitmentHistory);
        setLoaded(true);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const resolvedOrContinued = history.filter((h) => h.status === 'resolved' || h.status === 'continued').length;
  const abandonedCount = history.filter((h) => h.status === 'abandoned').length;

  return (
    <div className={styles.page}>
      {user && (
        <div className={styles.headerRow}>
          <div className={styles.avatar} style={{ background: user.avatarColor }}>
            {user.initials}
          </div>
          <div className={styles.identity}>
            <h1 className={styles.name}>{user.name}</h1>
            <div className={styles.meta}>
              {user.location} · member since {user.memberSince} · a public record of follow-through
            </div>
          </div>
          <div className={styles.reputationBlock}>
            <div className={styles.reputationNumber}>{user.reputation}</div>
            <div className={styles.reputationLabel}>Reputation</div>
          </div>
        </div>
      )}

      {loaded && (
        <div className={styles.grid}>
          <div>
            <div className={styles.sectionLabel}>
              Currently committed · {cards.length} / 3
            </div>
            <div className={styles.committedList}>
              {cards.map(({ summary, problem }) => {
                const daysLeft = summary.cycleLengthDays - summary.dayInCycle;
                return (
                  <div key={problem.id} className={styles.committedCard}>
                    <TierChip tier={problem.tier} />
                    <div className={styles.committedBody}>
                      <div className={styles.committedTitle}>{problem.title}</div>
                      <div className={styles.committedMeta}>
                        <RoleChip role={summary.role} /> · day {summary.dayInCycle} / {summary.cycleLengthDays}
                      </div>
                    </div>
                    <span className={daysLeft <= 7 ? styles.daysLeftUrgent : styles.daysLeft}>
                      {daysLeft}d left
                    </span>
                  </div>
                );
              })}
              {cards.length === 0 && <div className={styles.emptyState}>No problems committed yet.</div>}
            </div>

            <div className={`${styles.sectionLabel} ${styles.historyLabel}`}>Commitment history</div>
            <div className={styles.historyList}>
              {history.map((entry, i) => {
                const isAbandoned = entry.status === 'abandoned';
                return (
                  <div
                    key={`${entry.problemTitle}-${i}`}
                    className={`${styles.historyCard} ${isAbandoned ? styles.historyCardAbandoned : ''}`}
                  >
                    <span
                      className={`${styles.historyDot} ${isAbandoned ? styles.historyDotAbandoned : styles.historyDotOk}`}
                    />
                    <div className={styles.historyBody}>
                      <div className={styles.historyTitle}>{entry.problemTitle}</div>
                      <div className={`${styles.historyNote} ${isAbandoned ? styles.historyNoteAbandoned : ''}`}>
                        <RoleChip role={entry.role} /> · {entry.note}
                      </div>
                    </div>
                    <span
                      className={
                        isAbandoned
                          ? styles.historyStatusAbandoned
                          : entry.status === 'resolved'
                            ? styles.historyStatusResolved
                            : styles.historyStatusContinued
                      }
                    >
                      {STATUS_LABEL[entry.status]}
                    </span>
                  </div>
                );
              })}
              {history.length === 0 && <div className={styles.emptyState}>No commitment history yet.</div>}
            </div>
          </div>

          <div>
            <div className={styles.sectionLabel}>Badges · earned by follow-through</div>
            <div className={styles.badgeCard}>
              <div className={styles.badge}>
                <div className={`${styles.badgeIcon} ${styles.badgeIconFirst}`}>🕯</div>
                <div className={styles.badgeLabel}>First commitment</div>
              </div>
              <div className={styles.badge}>
                <div className={`${styles.badgeIcon} ${styles.badgeIconCycle}`}>✓</div>
                <div className={styles.badgeLabel}>Cycle completed</div>
              </div>
              <div className={styles.badge}>
                <div className={`${styles.badgeIcon} ${styles.badgeIconTier}`}>◆</div>
                <div className={styles.badgeLabel}>Resolved a B-tier</div>
              </div>
              <div className={`${styles.badge} ${styles.badgeLocked}`}>
                <div className={`${styles.badgeIcon} ${styles.badgeIconLocked}`}>◆</div>
                <div className={styles.badgeLabel}>Resolve an S-tier</div>
              </div>
            </div>

            <div className={styles.followThroughCard}>
              <div className={styles.followThroughLabel}>Follow-through rate</div>
              <div className={styles.followThroughNumber}>
                {resolvedOrContinued} of {history.length}
              </div>
              <div className={styles.followThroughNote}>
                cycles resolved or continued.
                {abandonedCount > 0
                  ? ` ${abandonedCount} abandonment${abandonedCount === 1 ? '' : 's'} on record.`
                  : ' No abandonments on record.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
