import { useState } from 'react';
import type { ActorSpecialization, Problem, Role } from '../../types/domain';
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
}

export function CommitModal({ problem, onClose }: CommitModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [role, setRole] = useState<Role | null>(null);
  const [specialization, setSpecialization] = useState<ActorSpecialization | null>(null);

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

          <div className={styles.actions}>
            <button type="button" className={styles.backButton} onClick={() => setStep(1)}>
              ← Back
            </button>
            <button type="button" className={styles.commitButton} onClick={onClose}>
              Commit — lock 90 days
            </button>
          </div>
        </div>
      )}
    </>
  );
}
