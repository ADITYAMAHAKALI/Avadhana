import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { rfpsPort } from '../data';
import { useOrganization } from '../context/OrganizationContext';
import { ApiError } from '../data/real/httpClient';
import type { ResolutionMode, RFPVisibility } from '../types/marketplace';
import { PageHeader } from '../components/shared/PageHeader';
import styles from './NewProblemPage.module.css';

const RESOLUTION_MODES: { value: ResolutionMode; label: string; desc: string }[] = [
  { value: 'marketplace', label: 'Marketplace matching', desc: 'Get a ranked shortlist of vendor Solutions.' },
  { value: 'community', label: 'Community-driven', desc: 'Promote into a civic Problem — subject to the 3-slot / 90-day mechanic (backend-only for now).' },
  { value: 'both', label: 'Both', desc: 'Promote to the community and get matched to vendors simultaneously.' },
];

export function NewRFPPage() {
  const navigate = useNavigate();
  const { activeOrganization } = useOrganization();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [budgetMin, setBudgetMin] = useState('');
  const [budgetMax, setBudgetMax] = useState('');
  const [timeline, setTimeline] = useState('');
  const [industry, setIndustry] = useState('');
  const [geography, setGeography] = useState('');
  const [resolutionMode, setResolutionMode] = useState<ResolutionMode>('marketplace');
  const [visibility, setVisibility] = useState<RFPVisibility>('public');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!activeOrganization) {
      setError('Create or select an Organization before posting an RFP.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const created = await rfpsPort.create({
        organizationId: activeOrganization.id,
        title,
        description,
        budgetMin: budgetMin ? Number(budgetMin) : null,
        budgetMax: budgetMax ? Number(budgetMax) : null,
        timeline,
        industry,
        geography,
        resolutionMode,
        visibility,
      });
      navigate(`/marketplace/rfps/${created.id}`, { replace: true });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not create this RFP. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={activeOrganization ? `Posting as ${activeOrganization.name}` : 'Marketplace'}
        title="Post an RFP"
        subtitle="Structured requirements you attach after creating drive the attribute-match score — add them from the RFP detail page once it's created."
      />

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fields}>
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Title</div>
            <input
              className={styles.input}
              type="text"
              placeholder="A short, specific RFP title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={300}
              required
            />
          </div>

          <div className={styles.field}>
            <div className={styles.fieldLabel}>Description</div>
            <textarea
              className={styles.textarea}
              placeholder="What are you procuring, and what does a good match look like?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={5000}
              required
            />
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Budget min (₹)</div>
              <input
                className={styles.input}
                type="number"
                min={0}
                placeholder="e.g. 50000"
                value={budgetMin}
                onChange={(e) => setBudgetMin(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Budget max (₹)</div>
              <input
                className={styles.input}
                type="number"
                min={0}
                placeholder="e.g. 500000"
                value={budgetMax}
                onChange={(e) => setBudgetMax(e.target.value)}
              />
            </div>
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Timeline</div>
              <input
                className={styles.input}
                type="text"
                placeholder="e.g. 6 weeks"
                value={timeline}
                onChange={(e) => setTimeline(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Industry</div>
              <input
                className={styles.input}
                type="text"
                placeholder="e.g. Environmental services"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Geography</div>
              <input
                className={styles.input}
                type="text"
                placeholder="e.g. Bhopal, MP"
                value={geography}
                onChange={(e) => setGeography(e.target.value)}
              />
            </div>
          </div>

          <div className={styles.field}>
            <div className={styles.fieldLabel}>Resolution mode</div>
            <div className={styles.tierGrid} style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {RESOLUTION_MODES.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  className={`${styles.tierCard} ${resolutionMode === m.value ? styles.tierCardSelected : ''}`}
                  onClick={() => setResolutionMode(m.value)}
                  title={m.desc}
                >
                  <div className={styles.tierCardLabel}>{m.label}</div>
                  <div className={styles.tierCardDesc}>{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <div className={styles.fieldLabel}>Visibility</div>
            <select
              className={styles.input}
              value={visibility}
              onChange={(e) => setVisibility(e.target.value as RFPVisibility)}
            >
              <option value="public">Public — anyone can see and match against it</option>
              <option value="invite_only">Invite-only — visible only to your Organization</option>
            </select>
          </div>
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        <div className={styles.actions}>
          <button type="button" className={styles.cancelButton} onClick={() => navigate(-1)} disabled={isSubmitting}>
            Cancel
          </button>
          <button type="submit" className={styles.submitButton} disabled={isSubmitting || !activeOrganization}>
            {isSubmitting ? 'Posting…' : 'Post RFP'}
          </button>
        </div>

        <div className={styles.finePrint}>
          Posting an RFP never spends a focus slot and is never locked for 90 days — the Marketplace is independent of
          the civic commitment mechanic. First 100 RFPs per Organization are free.
        </div>
      </form>
    </div>
  );
}
