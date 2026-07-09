import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { isUsingRealData, problemsPort } from '../data';
import { problemsApi } from '../data/real/problemsApi';
import { ApiError } from '../data/real/httpClient';
import { MockProblemsPort } from '../data/mock/MockProblemsPort';
import type { Tier } from '../types/domain';
import { PageHeader } from '../components/shared/PageHeader';
import { TierChip } from '../components/shared/TierChip';
import styles from './NewProblemPage.module.css';

/**
 * Condensed tier rubric shown inline next to the tier picker — full
 * reasoning lives in CLAUDE.md's "Tier Classification Rubric" subsection
 * (Key Architectural Decisions). Keep these two in sync if the ranges change.
 */
const TIER_RUBRIC: Record<Tier, { label: string; hours: string; funding: string; desc: string }> = {
  S: {
    label: 'Systemic / national',
    hours: '1,000+ hrs',
    funding: '₹50L+ or policy-scale (no $ figure)',
    desc: 'Policy change, legislation, large legal battles. Often open-ended, multi-cycle.',
  },
  A: {
    label: 'Large regional',
    hours: '200–1,000 hrs',
    funding: '₹5L – ₹50L',
    desc: 'City- or districtwide effort involving multiple institutions.',
  },
  B: {
    label: 'Community-scale',
    hours: '40–200 hrs',
    funding: '₹50k – ₹5L',
    desc: 'A neighborhood or defined local group; needs real Thinker/Actor/Backer division.',
  },
  C: {
    label: 'Small and local',
    hours: '8–40 hrs',
    funding: '₹5k – ₹50k',
    desc: 'A handful of people, light coordination, days to two weeks part-time.',
  },
  D: {
    label: 'Individually actionable',
    hours: '1–8 hrs',
    funding: '₹0 – ₹5k',
    desc: 'A single afternoon. One or two people, one fix, no fundraising needed.',
  },
};

const TIERS: Tier[] = ['S', 'A', 'B', 'C', 'D'];

export function NewProblemPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [location, setLocation] = useState('');
  const [category, setCategory] = useState('');
  const [tier, setTier] = useState<Tier | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!tier) {
      setError('Choose a tier before creating the problem.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const payload = { title, summary, location, category, tier };
      const created = isUsingRealData
        ? await problemsApi.create(payload)
        : await (problemsPort as MockProblemsPort).createProblem(payload);
      navigate(`/problems/${created.id}`, { replace: true });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'Could not create this problem. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Discovery starts here"
        title="Propose a problem"
        subtitle="Anyone can propose a problem — it becomes searchable immediately. Committing to work on it is a separate, deliberate step."
      />

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fields}>
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Title</div>
            <input
              className={styles.input}
              type="text"
              placeholder="A short, specific problem statement"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={300}
              required
            />
          </div>

          <div className={styles.field}>
            <div className={styles.fieldLabel}>Summary</div>
            <textarea
              className={styles.textarea}
              placeholder="What's the problem, what's the evidence, what would resolution look like?"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              maxLength={5000}
              required
            />
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Location</div>
              <input
                className={styles.input}
                type="text"
                placeholder="e.g. Pune, MH"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
              />
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Category</div>
              <input
                className={styles.input}
                type="text"
                placeholder="e.g. Environment, Safety, Policy"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
              />
            </div>
          </div>

          <div className={styles.field}>
            <div className={styles.fieldLabel}>Tier — estimated scale to resolution</div>
            <div className={styles.tierGrid}>
              {TIERS.map((t) => {
                const rubric = TIER_RUBRIC[t];
                return (
                  <button
                    key={t}
                    type="button"
                    className={`${styles.tierCard} ${tier === t ? styles.tierCardSelected : ''}`}
                    onClick={() => setTier(t)}
                    title={`${rubric.label} — ${rubric.hours}, ${rubric.funding}`}
                  >
                    <div className={styles.tierCardHead}>
                      <TierChip tier={t} />
                      <span className={styles.tierCardLabel}>{rubric.label}</span>
                    </div>
                    <div className={styles.tierCardRange}>
                      {rubric.hours}
                      <br />
                      {rubric.funding}
                    </div>
                  </button>
                );
              })}
            </div>
            {tier && (
              <div className={styles.tierDetail}>
                <div className={styles.tierDetailTitle}>
                  Tier {tier} — {TIER_RUBRIC[tier].label}
                </div>
                {TIER_RUBRIC[tier].desc} Roughly {TIER_RUBRIC[tier].hours} and {TIER_RUBRIC[tier].funding}.
              </div>
            )}
            <div className={styles.fieldHint}>
              Initial tier is a best guess — committed members can propose reclassification later as scope becomes clearer.
            </div>
          </div>
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        <div className={styles.actions}>
          <button type="button" className={styles.cancelButton} onClick={() => navigate(-1)} disabled={isSubmitting}>
            Cancel
          </button>
          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? 'Creating…' : 'Create problem'}
          </button>
        </div>

        <div className={styles.finePrint}>
          Creating a problem does not spend a focus slot. Only committing to work on it does — and that locks you in for
          a minimum of 90 days.
        </div>
      </form>
    </div>
  );
}
