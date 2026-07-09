import { useState } from 'react';
import type { ActorSpecialization, Problem, Role } from '../../types/domain';
import { commitmentsApi } from '../../data/real/commitmentsApi';
import { notifyFocusSlotsChanged } from '../../data/focusSlotsRefresh';
import { rememberCommitmentId } from '../../data/commitmentIdCache';
import { ApiError } from '../../data/real/httpClient';
import styles from './CommitModal.module.css';

const SPECIALIZATIONS: ActorSpecialization[] = [
  'Legal',
  'Research',
  'Content',
  'Web & app dev',
  'Ad campaign',
  'Field organizing',
];

const ROLE_NAME: Record<Role, string> = {
  thinker: 'Thinker',
  actor: 'Actor',
  backer: 'Backer',
};

interface CommitModalProps {
  problem: Problem;
  onClose: () => void;
  /** Called (in addition to onClose) after the commitment POST succeeds, so the host screen can refetch its own lock/problem state. Optional — defaults to no-op. */
  onCommitted?: () => void;
}

export function CommitModal({ problem, onClose, onCommitted }: CommitModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [role, setRole] = useState<Role | null>(null);
  const [specialization, setSpecialization] = useState<ActorSpecialization | null>(null);
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);

  async function handleCommit() {
    if (!role) return;
    setIsCommitting(true);
    setCommitError(null);
    try {
      const commitment = await commitmentsApi.create(problem.id, {
        role,
        specialization: role === 'actor' ? specialization : null,
      });
      // Stash commitment.id so the 90-day checkpoint flow (CheckpointModal)
      // can look it up by problem id later — the committed-problems list
      // endpoint only returns problem ids, not commitment ids. See
      // data/commitmentIdCache.ts for why this is needed.
      rememberCommitmentId(problem.id, commitment.id);
      notifyFocusSlotsChanged();
      onCommitted?.();
      onClose();
    } catch (err) {
      // Per the API contract, SLOT_LIMIT_EXCEEDED / ALREADY_COMMITTED come with
      // server-authored `message` text — surface that verbatim rather than
      // inventing our own copy, so the hard-block reads exactly as the backend intends.
      const message = err instanceof ApiError ? err.message : 'Could not commit to this problem. Please try again.';
      setCommitError(message);
    } finally {
      setIsCommitting(false);
    }
  }

  function pickRole(next: Role) {
    setRole(next);
    if (next !== 'actor') {
      setSpecialization(null);
    }
  }

  function roleCardClass(key: Role) {
    return `${styles.roleCard} ${role === key ? styles.roleCardSelected : ''}`;
  }

  function specChipClass(name: ActorSpecialization) {
    return `${styles.specChip} ${specialization === name ? styles.specChipSelected : ''}`;
  }

  const chosenRoleLabel = role ? ROLE_NAME[role] : '—';
  const chosenSpecLabel = specialization ? ` — ${specialization}` : '';

  return (
    <>
      <div className={styles.header}>
        <div className={styles.eyebrow}>COMMITTING A FOCUS SLOT</div>
        <div className={styles.headerTitle}>{problem.title}</div>
        <div className={styles.headerBody}>
          This spends 1 of your 3 slots and locks you in for a minimum of 90 days — no early exit. It&apos;s the earliest
          checkpoint, not a deadline to finish.
        </div>
      </div>

      {step === 1 && (
        <div className={styles.body}>
          <div className={styles.stepLabel}>Step 1 · Choose how you&apos;ll show up</div>
          <div className={styles.roleList}>
            <div className={roleCardClass('thinker')} onClick={() => pickRole('thinker')}>
              <div className={styles.roleCardHead}>
                <span className={`${styles.roleDot} ${styles.roleDotThinker}`} />
                <span className={styles.roleName}>Thinker</span>
              </div>
              <div className={styles.roleDesc}>Research, strategy, framing. No execution or funding required.</div>
            </div>

            <div className={roleCardClass('actor')} onClick={() => pickRole('actor')}>
              <div className={styles.roleCardHead}>
                <span className={`${styles.roleDot} ${styles.roleDotActor}`} />
                <span className={styles.roleName}>Actor</span>
              </div>
              <div className={styles.roleDesc}>On-ground execution — shaped by what the problem actually needs.</div>
              {role === 'actor' && (
                <div className={styles.specRow}>
                  {SPECIALIZATIONS.map((name) => (
                    <span
                      key={name}
                      className={specChipClass(name)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSpecialization(name);
                      }}
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className={roleCardClass('backer')} onClick={() => pickRole('backer')}>
              <div className={styles.roleCardHead}>
                <span className={`${styles.roleDot} ${styles.roleDotBacker}`} />
                <span className={styles.roleName}>Backer</span>
              </div>
              <div className={styles.roleDesc}>Financial contribution. No time commitment to think or act.</div>
            </div>
          </div>

          <div className={styles.actions}>
            <button type="button" className={styles.cancelButton} onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className={`${styles.nextButton} ${role ? '' : styles.nextButtonDisabled}`}
              disabled={!role}
              onClick={() => role && setStep(2)}
            >
              Continue →
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className={styles.body}>
          <div className={styles.stepLabel}>Step 2 · Confirm the lock</div>
          <div className={styles.confirmCard}>
            <svg width="96" height="96" viewBox="0 0 96 96">
              <circle cx="48" cy="48" r="40" fill="none" stroke="#EFE7D8" strokeWidth="9" />
              <circle
                cx="48"
                cy="48"
                r="40"
                fill="none"
                stroke="var(--color-saffron)"
                strokeWidth="9"
                strokeLinecap="round"
                strokeDasharray="251"
                strokeDashoffset="251"
                transform="rotate(-90 48 48)"
              />
              <text x="48" y="46" textAnchor="middle" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 20, fill: 'var(--color-ink)' }}>
                90
              </text>
              <text
                x="48"
                y="62"
                textAnchor="middle"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 8, fill: 'var(--color-ink-80)', letterSpacing: '0.06em' }}
              >
                MIN. DAYS
              </text>
            </svg>
            <div className={styles.confirmText}>
              <div>
                Role: <strong>{chosenRoleLabel}{chosenSpecLabel}</strong>
              </div>
              <div>
                Slot: <strong>3 of 3 — your last</strong>
              </div>
              <div>
                Minimum lock until: <strong>6 Oct 2026</strong>
              </div>
              <div className={styles.confirmNote}>Not a deadline — most problems take longer to actually resolve.</div>
              <div className={styles.confirmWarning}>Abandoning before the minimum counts against your record.</div>
            </div>
          </div>

          <label className={styles.ackRow}>
            <span className={styles.ackCheck}>✓</span>
            I understand I cannot free this slot for 90 days.
          </label>

          {commitError && <div className={styles.errorBanner}>{commitError}</div>}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.backButton}
              onClick={() => {
                setCommitError(null);
                setStep(1);
              }}
              disabled={isCommitting}
            >
              ← Back
            </button>
            <button type="button" className={styles.commitButton} onClick={handleCommit} disabled={isCommitting}>
              {isCommitting ? 'Committing…' : 'Commit — lock 90 days'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
