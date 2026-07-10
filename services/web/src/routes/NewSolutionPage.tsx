import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { solutionsPort } from '../data';
import { useOrganization } from '../context/OrganizationContext';
import { ApiError } from '../data/real/httpClient';
import { PageHeader } from '../components/shared/PageHeader';
import styles from './NewProblemPage.module.css';

export function NewSolutionPage() {
  const navigate = useNavigate();
  const { activeOrganization } = useOrganization();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!activeOrganization) {
      setError('Create or select an Organization before publishing a Solution.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const categoryTags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const created = await solutionsPort.create({
        organizationId: activeOrganization.id,
        title,
        description,
        categoryTags,
      });
      navigate(`/marketplace`, { state: { publishedSolutionId: created.id }, replace: true });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not publish this Solution. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={activeOrganization ? `Publishing as ${activeOrganization.name}` : 'Marketplace'}
        title="Publish a Solution"
        subtitle="Always free to publish — this is the provider-acquisition surface. Add structured attributes afterward to improve attribute-match scoring against RFPs."
      />

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fields}>
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Title</div>
            <input
              className={styles.input}
              type="text"
              placeholder="Your Solution's name"
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
              placeholder="What does this Solution do, and what kinds of RFPs is it a fit for?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={5000}
              required
            />
          </div>

          <div className={styles.field}>
            <div className={styles.fieldLabel}>Category tags</div>
            <input
              className={styles.input}
              type="text"
              placeholder="comma-separated, e.g. water-quality, hardware"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
            />
            <div className={styles.fieldHint}>Used for category-tag search filtering on the Marketplace browse screen.</div>
          </div>
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        <div className={styles.actions}>
          <button type="button" className={styles.cancelButton} onClick={() => navigate(-1)} disabled={isSubmitting}>
            Cancel
          </button>
          <button type="submit" className={styles.submitButton} disabled={isSubmitting || !activeOrganization}>
            {isSubmitting ? 'Publishing…' : 'Publish Solution'}
          </button>
        </div>

        <div className={styles.finePrint}>
          Solution publishing is always free — no quota, no billing gate, ever.
        </div>
      </form>
    </div>
  );
}
