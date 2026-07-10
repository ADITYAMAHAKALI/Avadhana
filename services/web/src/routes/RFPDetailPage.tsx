import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { matchingPort, rfpsPort } from '../data';
import { useOrganization } from '../context/OrganizationContext';
import { ApiError } from '../data/real/httpClient';
import type { AttributeMatch, RFP, RFPRequirement, SolutionMatch } from '../types/marketplace';
import { PageHeader } from '../components/shared/PageHeader';
import { Button } from '../components/shared/Button';
import styles from './RFPDetailPage.module.css';

type MatchTab = 'attribute' | 'rrf';

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 20; // ~1 minute of polling before giving up

function money(value: number | null): string {
  if (value === null) return '—';
  return `₹${value.toLocaleString('en-IN')}`;
}

function formatSignalName(key: string): string {
  return key.replace(/_/g, ' ');
}

export function RFPDetailPage() {
  const { rfpId } = useParams<{ rfpId: string }>();
  const { activeOrganization } = useOrganization();

  const [rfp, setRfp] = useState<RFP | null>(null);
  const [requirements, setRequirements] = useState<RFPRequirement[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [matchTab, setMatchTab] = useState<MatchTab>('attribute');

  const [attributeMatches, setAttributeMatches] = useState<AttributeMatch[]>([]);

  const [matchRunId, setMatchRunId] = useState<string | null>(null);
  const [matchRunStatus, setMatchRunStatus] = useState<string | null>(null);
  const [solutionMatches, setSolutionMatches] = useState<SolutionMatch[]>([]);
  const [isTriggering, setIsTriggering] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const pollAttemptsRef = useRef(0);
  const pollHandleRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isOwner = Boolean(activeOrganization && rfp && activeOrganization.id === rfp.organizationId);

  const load = useCallback(async () => {
    if (!rfpId) return;
    const [r, reqs, attrMatches, existing] = await Promise.all([
      rfpsPort.getById(rfpId),
      rfpsPort.listRequirements(rfpId),
      matchingPort.getAttributeMatches(rfpId),
      matchingPort.getMatches(rfpId),
    ]);
    setRfp(r);
    setRequirements(reqs);
    setAttributeMatches(attrMatches);
    setMatchRunId(existing.matchRun?.id ?? null);
    setMatchRunStatus(existing.matchRun?.status ?? null);
    setSolutionMatches(existing.matches);
    setLoaded(true);
  }, [rfpId]);

  useEffect(() => {
    let cancelled = false;
    load().catch(() => {
      if (!cancelled) setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  const stopPolling = useCallback(() => {
    if (pollHandleRef.current) {
      clearInterval(pollHandleRef.current);
      pollHandleRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Clean up any in-flight poll interval on unmount.
  useEffect(() => stopPolling, [stopPolling]);

  async function handleTriggerMatchRun() {
    if (!rfpId) return;
    setMatchError(null);
    setIsTriggering(true);
    try {
      const run = await matchingPort.triggerMatchRun(rfpId);
      setMatchRunId(run.id);
      setMatchRunStatus(run.status);
      setMatchTab('rrf');

      // Simple interval poll (per issue brief — no websockets) until the
      // run's status flips to a terminal state or we give up.
      pollAttemptsRef.current = 0;
      setIsPolling(true);
      pollHandleRef.current = setInterval(async () => {
        pollAttemptsRef.current += 1;
        try {
          const result = await matchingPort.getMatches(rfpId);
          if (result.matchRun) {
            setMatchRunId(result.matchRun.id);
            setMatchRunStatus(result.matchRun.status);
          }
          const terminal = result.matchRun?.status === 'completed' || result.matchRun?.status === 'failed';
          if (terminal) {
            setSolutionMatches(result.matches);
            stopPolling();
          } else if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
            stopPolling();
          }
        } catch {
          // Transient poll failure — keep trying until max attempts.
          if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) stopPolling();
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not start a matching run. Please try again.';
      setMatchError(message);
    } finally {
      setIsTriggering(false);
    }
  }

  if (loaded && !rfp) {
    return <div className={styles.notFound}>RFP not found.</div>;
  }

  if (!rfp) {
    return null;
  }

  const createdAtLabel = new Date(rfp.createdAt).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={`${rfp.resolutionMode} · ${rfp.visibility === 'invite_only' ? 'invite-only' : 'public'}`}
        title={rfp.title}
        subtitle={rfp.description}
      />

      <div className={styles.metaRow}>
        <span>{money(rfp.budgetMin)} – {money(rfp.budgetMax)}</span>
        <span>{rfp.timeline || 'No timeline given'}</span>
        <span>{rfp.industry || 'Any industry'}</span>
        <span>{rfp.geography || 'Any geography'}</span>
        <span>posted {createdAtLabel}</span>
        <span className={styles.statusBadge}>{rfp.status}</span>
      </div>

      <div className={styles.body}>
        <div className={styles.mainColumn}>
          <div className={styles.card}>
            <div className={styles.cardTitle}>Requirements</div>
            {requirements.length === 0 && <div className={styles.emptyInline}>No structured requirements added yet.</div>}
            {requirements.length > 0 && (
              <table className={styles.reqTable}>
                <thead>
                  <tr>
                    <th>Attribute</th>
                    <th>Value</th>
                    <th>Weight</th>
                    <th>Hard constraint?</th>
                  </tr>
                </thead>
                <tbody>
                  {requirements.map((req) => (
                    <tr key={req.id}>
                      <td>{req.attributeKey}</td>
                      <td>{req.attributeValue}</td>
                      <td>{req.weight}</td>
                      <td>{req.isHardConstraint ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className={styles.card}>
            <div className={styles.matchTabs}>
              <button
                type="button"
                className={`${styles.matchTab} ${matchTab === 'attribute' ? styles.matchTabActive : ''}`}
                onClick={() => setMatchTab('attribute')}
              >
                Attribute matches
              </button>
              <button
                type="button"
                className={`${styles.matchTab} ${matchTab === 'rrf' ? styles.matchTabActive : ''}`}
                onClick={() => setMatchTab('rrf')}
              >
                Ranked shortlist (RRF)
              </button>
            </div>

            {matchTab === 'attribute' && (
              <div className={styles.matchList}>
                {attributeMatches.length === 0 && (
                  <div className={styles.emptyInline}>No attribute matches yet — add requirements and Solutions need matching attributes.</div>
                )}
                {attributeMatches.map((m) => (
                  <div className={styles.matchRow} key={m.solution.id}>
                    <div>
                      <div className={styles.matchSolutionTitle}>{m.solution.title}</div>
                      <div className={styles.matchSolutionDesc}>{m.solution.description}</div>
                    </div>
                    <div className={styles.matchScoreCol}>
                      <div className={styles.matchScore}>{(m.score * 100).toFixed(0)}%</div>
                      <div className={styles.matchScoreLabel}>{m.matchedRequirementIds.length} req(s) matched</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {matchTab === 'rrf' && (
              <div>
                <div className={styles.rrfHeader}>
                  <div>
                    <div className={styles.rrfExplain}>
                      Fuses the attribute-match score with per-embedding-space semantic similarity via reciprocal rank
                      fusion — each signal is ranked, not just scored, so a buyer can see exactly why a Solution ranked
                      where it did.
                    </div>
                    {matchRunStatus && (
                      <div className={styles.rrfStatus}>
                        Last run: <strong>{matchRunStatus}</strong>
                        {isPolling && ' · polling for results…'}
                      </div>
                    )}
                  </div>
                  <Button
                    variant="primary"
                    onClick={handleTriggerMatchRun}
                    disabled={!isOwner || isTriggering || isPolling}
                    title={isOwner ? undefined : 'Only a member of the posting Organization can run matching.'}
                  >
                    {isTriggering || isPolling ? 'Running…' : 'Run matching'}
                  </Button>
                </div>

                {matchError && <div className={styles.errorBanner}>{matchError}</div>}

                {!matchRunId && solutionMatches.length === 0 && (
                  <div className={styles.emptyInline}>No matching run yet. Click &quot;Run matching&quot; to compute a ranked shortlist.</div>
                )}

                {solutionMatches.length > 0 && (
                  <div className={styles.matchList}>
                    {solutionMatches.map((m) => (
                      <div className={styles.rrfMatchCard} key={m.id}>
                        <div className={styles.rrfMatchHead}>
                          <span className={styles.rrfRank}>#{m.rank}</span>
                          <div>
                            <div className={styles.matchSolutionTitle}>{m.solution.title}</div>
                            <div className={styles.matchSolutionDesc}>{m.solution.description}</div>
                          </div>
                          <div className={styles.matchScoreCol}>
                            <div className={styles.matchScore}>{m.finalRrfScore.toFixed(4)}</div>
                            <div className={styles.matchScoreLabel}>fused RRF score</div>
                          </div>
                        </div>
                        <div className={styles.signalBreakdown}>
                          {Object.entries(m.signalScores).map(([signal, score]) => (
                            <div className={styles.signalRow} key={signal}>
                              <span className={styles.signalName}>{formatSignalName(signal)}</span>
                              <div className={styles.signalBarTrack}>
                                <div className={styles.signalBarFill} style={{ width: `${Math.min(100, score * 100)}%` }} />
                              </div>
                              <span className={styles.signalValue}>
                                {score.toFixed(2)} (rank {m.signalRanks[signal] ?? '—'})
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
