import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { PageHeader } from '../components/shared/PageHeader';
import { Button } from '../components/shared/Button';
import { moderationPort, problemsPort } from '../data';
import type { InvocationLogEntry, ModerationQueueItem, Problem } from '../types/domain';
import styles from './CoordinatorPage.module.css';

export function CoordinatorPage() {
  const { problemId = '' } = useParams<{ problemId: string }>();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [queue, setQueue] = useState<ModerationQueueItem[]>([]);
  const [log, setLog] = useState<InvocationLogEntry[]>([]);
  const [stats, setStats] = useState({ autoBlocked: 0, flagged: 0, openAppeals: 0 });

  useEffect(() => {
    problemsPort.getById(problemId).then(setProblem);
    moderationPort.getQueue(problemId).then(setQueue);
    moderationPort.getInvocationLog(problemId).then(setLog);
    moderationPort.getStats(problemId).then(setStats);
  }, [problemId]);

  const eyebrow = problem ? problem.title : 'Problem coordinator';

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={eyebrow}
        title="Coordinator & moderation"
        subtitle="The AI enforces focus and flags drift. Humans decide. Every action is logged, immutable, and visible to committed members."
      />

      <div className={styles.statRow}>
        <div className={styles.statCard}>
          <div className={styles.statNumber}>{stats.autoBlocked}</div>
          <div className={styles.statLabel}>Auto-blocked (high confidence)</div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statNumber} ${styles.statNumberFlagged}`}>{stats.flagged}</div>
          <div className={styles.statLabel}>Flagged for human review</div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statNumber} ${styles.statNumberAppeal}`}>{stats.openAppeals}</div>
          <div className={styles.statLabel}>Open appeal</div>
        </div>
      </div>

      <div className={styles.columns}>
        <div>
          <div className={styles.sectionLabel}>Review queue</div>
          <div className={styles.queueList}>
            {queue.map((item) => (
              <QueueCard key={item.id} item={item} />
            ))}
          </div>
        </div>

        <div>
          <div className={styles.sectionLabel}>AI invocation log · immutable</div>
          <div className={styles.logCard}>
            {log.map((entry) => (
              <div key={entry.id} className={styles.logRow}>
                <div className={styles.logRowTop}>
                  <span className={styles.logType}>{entry.type}</span>
                  <span className={styles.logTime}>{entry.timeAgo}</span>
                </div>
                <div className={styles.logDetail}>{entry.detail}</div>
              </div>
            ))}
          </div>

          <div className={styles.calibrationNote}>
            Appeals feed model calibration. Denied appeals that were genuinely off-topic strengthen detection;
            reversed blocks correct false positives.
          </div>
        </div>
      </div>
    </div>
  );
}

function QueueCard({ item }: { item: ModerationQueueItem }) {
  const isFlagged = item.status === 'flagged';

  return (
    <div className={styles.queueCard}>
      <div className={styles.queueCardTop}>
        <span className={isFlagged ? styles.pillFlagged : styles.pillBlocked}>
          {isFlagged ? 'Flagged · off-topic' : 'Auto-blocked'}
        </span>
        <span className={styles.confidence}>confidence {item.confidence.toFixed(2)}</span>
        <span className={styles.timeAgo}>
          {item.timeAgo}
          {item.appealFiled ? ' · appealed' : ''}
        </span>
      </div>

      <div className={isFlagged ? styles.body : styles.bodyBlocked}>&quot;{item.body}&quot;</div>

      <div className={styles.authorLine}>
        by {item.author} · {item.authorNote}
        {item.appealFiled && <span className={styles.appealFiled}> · appeal filed</span>}
      </div>

      <div className={styles.actions}>
        {isFlagged ? (
          <>
            <Button variant="dark" className={styles.upholdBtn}>
              Uphold block
            </Button>
            <Button variant="secondary" className={styles.allowBtn}>
              Allow
            </Button>
            <Button variant="ghost">Suggest split →</Button>
          </>
        ) : (
          <>
            <Button variant="dark">Deny appeal</Button>
            <Button variant="ghost">Reverse block</Button>
          </>
        )}
      </div>
    </div>
  );
}
