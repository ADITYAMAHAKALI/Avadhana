import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { currentUserPort, problemsPort } from '../data';
import type { CommittedProblemSummary, Problem } from '../types/domain';
import { Button } from '../components/shared/Button';
import { ClockRing } from '../components/shared/ClockRing';
import { Modal } from '../components/shared/Modal';
import { PageHeader } from '../components/shared/PageHeader';
import { RoleChip } from '../components/shared/RoleChip';
import { TierChip } from '../components/shared/TierChip';
import { CheckpointModal } from '../components/CheckpointModal/CheckpointModal';
import { subscribeFocusSlotsRefresh } from '../data/focusSlotsRefresh';
import styles from './DashboardPage.module.css';

interface CommittedCard {
  summary: CommittedProblemSummary;
  problem: Problem;
}

const TODAY_LABEL = new Date().toLocaleDateString('en-US', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
});

export function DashboardPage() {
  const [cards, setCards] = useState<CommittedCard[]>([]);
  const [slots, setSlots] = useState({ used: 0, total: 3 });
  const [loaded, setLoaded] = useState(false);
  const [checkpointProblem, setCheckpointProblem] = useState<Problem | null>(null);

  const load = useCallback(async () => {
    const [committed, slotCount] = await Promise.all([
      currentUserPort.getCommittedProblems(),
      currentUserPort.getFocusSlotCount(),
    ]);
    const joined = await Promise.all(
      committed.map(async (summary) => {
        const problem = await problemsPort.getById(summary.problemId);
        return problem ? { summary, problem } : null;
      }),
    );
    setCards(joined.filter((c): c is CommittedCard => c !== null));
    setSlots(slotCount);
    setLoaded(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    load().catch(() => {
      if (!cancelled) setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  // Refetch after a checkpoint (or a commitment) changes elsewhere in the
  // tree — same pub/sub CommitModal already uses (data/focusSlotsRefresh.ts)
  // rather than plumbing a callback through every possible caller.
  useEffect(() => subscribeFocusSlotsRefresh(() => void load()), [load]);

  const openSlots = Math.max(0, slots.total - slots.used);

  // A checkpoint is due once dayInCycle has reached (or passed) the 90-day
  // minimum — the frontend's own math is the source of truth for *showing*
  // the affordance; the backend re-validates on submit regardless (and
  // would 409 LOCK_ACTIVE if this math were ever wrong, e.g. clock skew).
  function isCheckpointDue(summary: CommittedProblemSummary): boolean {
    return summary.dayInCycle >= summary.cycleLengthDays;
  }

  // Checkpoint banner: whichever committed problem is nearest its 90-day checkpoint.
  const checkpoint = cards.reduce<CommittedCard | null>((closest, card) => {
    const remaining = card.summary.cycleLengthDays - card.summary.dayInCycle;
    if (remaining < 0) return closest;
    if (!closest) return card;
    const closestRemaining = closest.summary.cycleLengthDays - closest.summary.dayInCycle;
    return remaining < closestRemaining ? card : closest;
  }, null);

  const problemCountLabel =
    cards.length === 0 ? 'No problems committed yet.' : `${cards.length} problem${cards.length === 1 ? '' : 's'} committed.`;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={TODAY_LABEL}
        title="Your focus"
        subtitle={`${problemCountLabel} Everything you owe is here — nothing else.`}
        actions={
          <Link to="/discover">
            <Button variant="secondary">Find a problem →</Button>
          </Link>
        }
      />

      {checkpoint && (
        <div className={styles.checkpoint}>
          <div className={styles.checkpointBar} />
          <div className={styles.checkpointBody}>
            <div className={styles.checkpointTitle}>
              {isCheckpointDue(checkpoint.summary)
                ? `Checkpoint due · ${checkpoint.problem.title}`
                : `Checkpoint in ${checkpoint.summary.cycleLengthDays - checkpoint.summary.dayInCycle} days · ${checkpoint.problem.title}`}
            </div>
            <div className={styles.checkpointMeta}>
              Day {checkpoint.summary.dayInCycle} of {checkpoint.summary.cycleLengthDays}. You&apos;ll be asked to mark it resolved,
              continue, or abandon.
            </div>
          </div>
          <button
            className={styles.reviewButton}
            type="button"
            disabled={!isCheckpointDue(checkpoint.summary)}
            title={isCheckpointDue(checkpoint.summary) ? undefined : 'Not due yet — the lock is still active.'}
            onClick={() => setCheckpointProblem(checkpoint.problem)}
          >
            Review
          </button>
        </div>
      )}

      {loaded && (
        <div className={styles.grid}>
          {cards.map(({ summary, problem }) => {
            const daysLeft = summary.cycleLengthDays - summary.dayInCycle;
            const due = isCheckpointDue(summary);
            return (
              <div key={problem.id} className={styles.card}>
                <div className={styles.cardTop}>
                  <TierChip tier={problem.tier} />
                  <ClockRing size={58} strokeWidth={6} progress={summary.dayInCycle / summary.cycleLengthDays} centerText={String(daysLeft)} />
                </div>
                <div className={styles.cardTitle}>{problem.title}</div>
                <div className={styles.cardMeta}>
                  {problem.location} · Day {summary.dayInCycle} / {summary.cycleLengthDays}
                </div>
                <div className={styles.roleRow}>
                  <RoleChip role={summary.role} prefix="You" />
                </div>
                {due && (
                  <div className={styles.checkpointDueRow}>
                    <span className={styles.checkpointDueBadge}>Checkpoint due</span>
                    <button
                      type="button"
                      className={styles.checkpointDueButton}
                      onClick={() => setCheckpointProblem(problem)}
                    >
                      Review →
                    </button>
                  </div>
                )}
                <div className={styles.cardFooter}>
                  <div className={styles.footerLabel}>NEXT TASK · YOURS</div>
                  <div className={styles.footerTask}>{summary.nextTask ?? 'No task assigned yet'}</div>
                </div>
              </div>
            );
          })}

          {Array.from({ length: openSlots }).map((_, i) => (
            <Link to="/discover" key={`open-slot-${i}`} className={styles.openSlotCard}>
              <div className={styles.openSlotIcon}>+</div>
              <div className={styles.openSlotTitle}>One slot open</div>
              <div className={styles.openSlotBody}>Choose deliberately. You can&apos;t free it again for 90 days.</div>
              <Button variant="primary" type="button">
                Browse problems
              </Button>
            </Link>
          ))}
        </div>
      )}

      {checkpointProblem && (
        <Modal onClose={() => setCheckpointProblem(null)}>
          <CheckpointModal
            problem={checkpointProblem}
            onClose={() => setCheckpointProblem(null)}
            onCheckpointed={load}
          />
        </Modal>
      )}
    </div>
  );
}
