import { useState } from 'react';
import type { CheckpointAction } from '../../data/real/commitmentsApi';
import { commitmentsApi } from '../../data/real/commitmentsApi';
import { getCommitmentId } from '../../data/commitmentIdCache';
import { notifyFocusSlotsChanged } from '../../data/focusSlotsRefresh';
import { ApiError } from '../../data/real/httpClient';
import type { Problem } from '../../types/domain';
import styles from './CheckpointModal.module.css';

interface ActionOption {
  key: CheckpointAction;
  label: string;
  description: string;
}

const ACTIONS: ActionOption[] = [
  {
    key: 'resolve',
    label: 'Resolve',
    description: 'Mark this problem solved. Frees your slot and counts as a completed 90-day cycle.',
  },
  {
    key: 'continue',
    label: 'Continue',
    description: 'Stay committed for another full cycle. Your slot stays spent — no early exit still applies.',
  },
  {
    key: 'abandon',
    label: 'Abandon',
    description:
      'Free your slot without resolving. This is a real cost: it is recorded on your profile and counts against your reputation, permanently.',
  },
];

interface CheckpointModalProps {
  problem: Problem;
  onClose: () => void;
  /** Called after a successful checkpoint POST, so the host screen (DashboardPage) can refetch committed-problems. */
  onCheckpointed?: () => void;
}

export function CheckpointModal({ problem, onClose, onCheckpointed }: CheckpointModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [action, setAction] = useState<CheckpointAction | null>(null);
  const [note, setNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [daysRemaining, setDaysRemaining] = useState<number | null>(null);

  const commitmentId = getCommitmentId(problem.id);

  async function handleConfirm() {
    if (!action) return;
    if (!commitmentId) {
      // Real gap in the current API contract: GET /users/me/committed-problems
      // returns problemId but not commitmentId, and there's no lookup
      // endpoint from problemId -> commitmentId. We cache commitmentId
      // client-side at commit time (see data/commitmentIdCache.ts) — if
      // that cache is empty (commitment predates this feature, or a
      // different browser/session), we can't resolve which commitment to
      // checkpoint without a backend change that's out of scope here.
      setError(
        "Couldn't find this commitment's id locally, so the checkpoint can't be submitted from this browser. Try again from the device/browser you committed on.",
      );
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setDaysRemaining(null);
    try {
      await commitmentsApi.checkpoint(commitmentId, action, note.trim() ? note.trim() : null);
      notifyFocusSlotsChanged();
      onCheckpointed?.();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.code === 'LOCK_ACTIVE') {
        // Shouldn't happen in the normal flow (the affordance only shows
        // once the frontend's own dayInCycle math says the checkpoint is
        // due) but guard against clock-skew/race edge cases and surface the
        // server's own daysRemaining rather than inventing copy.
        const body = err.body as { daysRemaining?: number } | undefined;
        setDaysRemaining(body?.daysRemaining ?? null);
        setError(err.message);
      } else {
        setError(err instanceof ApiError ? err.message : 'Could not submit the checkpoint. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function actionCardClass(key: CheckpointAction) {
    const base = `${styles.actionCard} ${action === key ? styles.actionCardSelected : ''}`;
    return key === 'abandon' ? `${base} ${styles.actionCardAbandon}` : base;
  }

  const chosen = ACTIONS.find((a) => a.key === action) ?? null;

  return (
    <>
      <div className={styles.header}>
        <div className={styles.eyebrow}>90-DAY CHECKPOINT</div>
        <div className={styles.headerTitle}>{problem.title}</div>
        <div className={styles.headerBody}>
          You&apos;ve reached the minimum commitment period. Choose how you want to proceed — this is recorded on
          your profile either way.
        </div>
      </div>

      {step === 1 && (
        <div className={styles.body}>
          <div className={styles.stepLabel}>Step 1 · Choose an outcome</div>
          <div className={styles.actionList}>
            {ACTIONS.map((opt) => (
              <div key={opt.key} className={actionCardClass(opt.key)} onClick={() => setAction(opt.key)}>
                <div className={styles.actionCardHead}>
                  <span className={styles.actionName}>{opt.label}</span>
                </div>
                <div className={styles.actionDesc}>{opt.description}</div>
              </div>
            ))}
          </div>

          <div className={styles.actions}>
            <button type="button" className={styles.cancelButton} onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className={`${styles.nextButton} ${action ? '' : styles.nextButtonDisabled}`}
              disabled={!action}
              onClick={() => action && setStep(2)}
            >
              Continue →
            </button>
          </div>
        </div>
      )}

      {step === 2 && chosen && (
        <div className={styles.body}>
          <div className={styles.stepLabel}>Step 2 · Confirm</div>

          <div className={`${styles.confirmCard} ${action === 'abandon' ? styles.confirmCardAbandon : ''}`}>
            <div className={styles.confirmText}>
              <div>
                Outcome: <strong>{chosen.label}</strong>
              </div>
              <div className={styles.confirmDesc}>{chosen.description}</div>
              {action === 'abandon' && (
                <div className={styles.confirmWarning}>
                  This cannot be undone and will show as an abandoned commitment on your public profile.
                </div>
              )}
            </div>
          </div>

          <label className={styles.noteLabel}>
            Note (optional)
            <textarea
              className={styles.noteInput}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder={
                action === 'resolve'
                  ? 'What was the resolution?'
                  : action === 'abandon'
                    ? 'Why are you stepping away?'
                    : 'Anything worth recording for the next cycle?'
              }
            />
          </label>

          {error && (
            <div className={styles.errorBanner}>
              {error}
              {daysRemaining != null && <> ({daysRemaining} day{daysRemaining === 1 ? '' : 's'} remaining.)</>}
            </div>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.backButton}
              onClick={() => {
                setError(null);
                setStep(1);
              }}
              disabled={isSubmitting}
            >
              ← Back
            </button>
            <button
              type="button"
              className={`${styles.confirmButton} ${action === 'abandon' ? styles.confirmButtonAbandon : ''}`}
              onClick={handleConfirm}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Submitting…' : `Confirm — ${chosen.label.toLowerCase()}`}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
