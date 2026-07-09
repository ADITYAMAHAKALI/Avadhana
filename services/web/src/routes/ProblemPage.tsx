import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { currentUserPort, problemsPort } from '../data';
import type { CommittedProblemSummary, FeedPost, Problem, TaskItem } from '../types/domain';
import { Button } from '../components/shared/Button';
import { ClockRing } from '../components/shared/ClockRing';
import { Modal } from '../components/shared/Modal';
import { CommitModal } from '../components/CommitModal/CommitModal';
import styles from './ProblemPage.module.css';

const TASK_BOX_CLASS: Record<TaskItem['status'], string> = {
  done: styles.taskBoxDone,
  open: styles.taskBoxOpen,
  unclaimed: styles.taskBoxUnclaimed,
};

export function ProblemPage() {
  const { problemId } = useParams<{ problemId: string }>();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [feed, setFeed] = useState<FeedPost[]>([]);
  const [lock, setLock] = useState<CommittedProblemSummary | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [showCommit, setShowCommit] = useState(false);

  const load = useCallback(async () => {
    if (!problemId) return;
    const [p, t, f, committed] = await Promise.all([
      problemsPort.getById(problemId),
      problemsPort.getTasks(problemId),
      problemsPort.getFeed(problemId),
      currentUserPort.getCommittedProblems(),
    ]);
    setProblem(p);
    setTasks(t);
    setFeed(f);
    setLock(committed.find((c) => c.problemId === problemId) ?? committed[0] ?? null);
    setLoaded(true);
  }, [problemId]);

  useEffect(() => {
    let cancelled = false;
    load().catch(() => {
      if (!cancelled) setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  if (loaded && !problem) {
    return <div className={styles.notFound}>Problem not found.</div>;
  }

  if (!problem) {
    return null;
  }

  const dayInCycle = lock?.dayInCycle ?? 86;
  const cycleLengthDays = lock?.cycleLengthDays ?? 90;
  const daysRemaining = Math.max(0, cycleLengthDays - dayInCycle);
  const createdAtLabel = new Date(problem.createdAt).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.breadcrumb}>
          <a>Discover</a>
          {problem.parentProblemTitle && (
            <>
              {' '}
              · Parent: <a>{problem.parentProblemTitle}</a>
            </>
          )}
        </div>
        <div className={styles.headerRow}>
          <span className={styles.tierBadge}>{problem.tier}</span>
          <div className={styles.titleBlock}>
            <h1 className={styles.title}>{problem.title}</h1>
            <div className={styles.meta}>
              {problem.location} · {problem.category} · created {createdAtLabel} · tier {problem.tier}{' '}
              <a className={styles.disputeLink}>(dispute tier)</a>
            </div>
          </div>
          <div className={styles.headerActions}>
            <Button variant="secondary">↗ Share</Button>
            <Button variant="primary" onClick={() => setShowCommit(true)}>
              Commit a slot
            </Button>
          </div>
        </div>
      </div>

      <div className={styles.body}>
        {/* feed column */}
        <div className={styles.feedColumn}>
          <div className={styles.tabs}>
            <button type="button" className={`${styles.tab} ${styles.tabActive}`}>
              Feed
            </button>
            <button type="button" className={styles.tab}>
              Tasks · {tasks.length}
            </button>
            <button type="button" className={styles.tab}>
              Assets · 4
            </button>
            <button type="button" className={styles.tab}>
              Members · {problem.thinkerCount + problem.actorCount + problem.backerCount}
            </button>
          </div>

          <div className={styles.summaryCard}>
            <div className={styles.summaryHead}>
              <span className={styles.summaryMark}>✦</span>
              <span className={styles.summaryTitle}>SARVAM Coordinator · summary</span>
              <span className={styles.summaryTime}>updated 3h ago</span>
            </div>
            <div className={styles.summaryBody}>
              Testing at 3 borewells confirms nitrate above safe limits. The group agreed to pursue an RTI on the water
              board&apos;s internal logs before escalating. Two actors are meeting the ward officer Thursday; funding for
              lab re-tests (₹18k) is the open blocker.
            </div>
          </div>

          <div className={styles.gateNotice}>
            <span>🔒</span>
            <span className={styles.gateText}>
              Only committed members can post here.{' '}
              <button type="button" className={styles.gateLink} onClick={() => setShowCommit(true)}>
                Commit a slot to join the discussion.
              </button>
            </span>
          </div>

          <div className={styles.posts}>
            {feed.map((post) => (
              <div className={styles.post} key={post.id}>
                <div className={styles.avatar} style={{ background: post.authorColor }}>
                  {post.authorInitials}
                </div>
                <div className={styles.postBody}>
                  <div className={styles.postHead}>
                    <span className={styles.postAuthor}>{post.authorName}</span>
                    <span className={styles.postRole}>{post.roleLabel}</span>
                    <span className={styles.postTime}>{post.timeAgo}</span>
                  </div>
                  <div className={styles.postText}>{post.body}</div>

                  {post.poll && (
                    <div className={styles.poll}>
                      {post.poll.options.map((opt) => (
                        <div className={styles.pollBar} key={opt.label}>
                          <div className={styles.pollFill} style={{ right: `${100 - opt.percent}%` }} />
                          <div className={styles.pollRow}>
                            <span>{opt.label}</span>
                            <span style={{ fontWeight: 600 }}>{opt.percent}%</span>
                          </div>
                        </div>
                      ))}
                      <div className={styles.pollMeta}>
                        {post.poll.committedVoters} committed members · closes in {post.poll.closesInDays} days
                      </div>
                    </div>
                  )}

                  {!post.poll && (
                    <div className={styles.postActions}>
                      <span>♥ {post.likeCount}</span>
                      <span>Reply</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* right rail */}
        <div className={styles.rightRail}>
          <div className={`${styles.card} ${styles.lockCard}`}>
            <ClockRing size={72} strokeWidth={8} progress={dayInCycle / cycleLengthDays} centerText={String(daysRemaining)} />
            <div>
              <div className={styles.lockTitle}>Your lock</div>
              <div className={styles.lockMeta}>
                Day {dayInCycle} / {cycleLengthDays} · checkpoint 12 Jul. Minimum only — most problems take longer to
                finish.
              </div>
            </div>
          </div>

          <div className={`${styles.card} ${styles.tasksCard}`}>
            <div className={styles.cardHeadRow}>
              <span className={styles.cardHeadTitle}>Task checklist</span>
              <span className={styles.cardHeadBadge}>AI-drafted</span>
            </div>
            <div className={styles.taskList}>
              {tasks.map((task) => (
                <div className={styles.taskRow} key={task.id}>
                  <span className={`${styles.taskBox} ${TASK_BOX_CLASS[task.status]}`}>
                    {task.status === 'done' ? '✓' : ''}
                  </span>
                  <span className={`${styles.taskLabel} ${task.status === 'done' ? styles.taskLabelDone : ''}`}>
                    {task.label}{' '}
                    {task.status === 'unclaimed' ? (
                      <span className={styles.taskUnclaimed}>· unclaimed</span>
                    ) : task.assignee ? (
                      <span className={styles.taskAssignee}>· {task.assignee}</span>
                    ) : null}
                  </span>
                </div>
              ))}
            </div>
            <button type="button" className={styles.pickupButton}>
              Pick up a task
            </button>
          </div>

          <div className={`${styles.card} ${styles.membersCard}`}>
            <div className={styles.membersTitle}>
              Committed · {problem.thinkerCount + problem.actorCount + problem.backerCount}
            </div>
            <div className={styles.membersBreakdown}>
              <span>
                <span className={styles.breakdownThinker}>{problem.thinkerCount}</span> thinkers
              </span>
              <span>
                <span className={styles.breakdownActor}>{problem.actorCount}</span> actors
              </span>
              <span>
                <span className={styles.breakdownBacker}>{problem.backerCount}</span> backer
              </span>
            </div>
            <div className={styles.avatarStack}>
              <span className={styles.stackAvatar} style={{ background: 'var(--color-thinker)' }}>
                RM
              </span>
              <span className={styles.stackAvatar} style={{ background: 'var(--color-actor)' }}>
                AS
              </span>
              <span className={styles.stackAvatar} style={{ background: 'var(--color-thinker)' }}>
                DK
              </span>
              <span className={styles.stackAvatar} style={{ background: 'var(--color-backer)' }}>
                PN
              </span>
              <span className={`${styles.stackAvatar} ${styles.stackAvatarMore}`}>+4</span>
            </div>
          </div>

          <button type="button" className={styles.invokeButton}>
            ✦ Invoke coordinator
          </button>
        </div>
      </div>

      {showCommit && (
        <Modal onClose={() => setShowCommit(false)}>
          <CommitModal problem={problem} onClose={() => setShowCommit(false)} onCommitted={load} />
        </Modal>
      )}
    </div>
  );
}
