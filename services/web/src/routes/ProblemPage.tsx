import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { currentUserPort, problemsPort } from '../data';
import type { Comment, CommittedProblemSummary, FeedPost, FeedSort, Problem, TaskItem } from '../types/domain';
import { Button } from '../components/shared/Button';
import { ClockRing } from '../components/shared/ClockRing';
import { Modal } from '../components/shared/Modal';
import { CommitModal } from '../components/CommitModal/CommitModal';
import { feedApi } from '../data/real/feedApi';
import { ApiError } from '../data/real/httpClient';
import styles from './ProblemPage.module.css';

const TASK_BOX_CLASS: Record<TaskItem['status'], string> = {
  done: styles.taskBoxDone,
  open: styles.taskBoxOpen,
  unclaimed: styles.taskBoxUnclaimed,
};

// Visual nesting cap (issue #98) — the backend stores an arbitrarily deep
// parent_comment_id chain with no depth enforcement (a deep chain isn't
// harmful by itself), but a UI that keeps indenting forever becomes
// unreadable. 6 levels is a typical Reddit-style cap: past this depth,
// replies still nest logically (a reply to a level-6 comment is still a
// reply to it) but stop gaining additional left-indent, so the thread
// doesn't get pushed off-screen.
const MAX_VISUAL_DEPTH = 6;

interface CommentTreeNode {
  comment: Comment;
  children: CommentTreeNode[];
}

/**
 * Builds a nested tree from the flat parent-pointer list the backend
 * returns (see feedApi.getComments / backend `list_comments_for_post`
 * docstring — deliberately flat, not a recursive tree query). Comments
 * whose `parentCommentId` doesn't resolve to another comment in the same
 * list (or is null) are treated as top-level, so a reply to a
 * hidden/moderated-away parent still renders instead of vanishing.
 */
function buildCommentTree(comments: Comment[]): CommentTreeNode[] {
  const byId = new Map<string, CommentTreeNode>();
  for (const comment of comments) {
    byId.set(comment.id, { comment, children: [] });
  }
  const roots: CommentTreeNode[] = [];
  for (const comment of comments) {
    const node = byId.get(comment.id)!;
    const parent = comment.parentCommentId ? byId.get(comment.parentCommentId) : undefined;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

interface CommentThreadNodeProps {
  node: CommentTreeNode;
  postId: string;
  depth: number;
  isCommitted: boolean;
  activeReplyTarget: string | null;
  commentDrafts: Record<string, string>;
  commentPosting: Set<string>;
  commentErrors: Record<string, string>;
  onToggleReplyTarget: (postId: string, commentId: string) => void;
  onDraftChange: (composerKey: string, value: string) => void;
  onSubmitReply: (postId: string, composerKey: string, parentCommentId: string) => void;
  onRequestCommit: () => void;
}

/**
 * Recursive per-comment renderer (issue #98): renders one comment, then
 * recurses into its children. Visual indentation (`.commentChildren`'s
 * left padding/border) increases per level up to MAX_VISUAL_DEPTH —
 * past that, replies keep nesting logically but stop indenting further
 * so a long thread doesn't get pushed off-screen.
 */
function CommentThreadNode({
  node,
  postId,
  depth,
  isCommitted,
  activeReplyTarget,
  commentDrafts,
  commentPosting,
  commentErrors,
  onToggleReplyTarget,
  onDraftChange,
  onSubmitReply,
  onRequestCommit,
}: CommentThreadNodeProps) {
  const { comment, children } = node;
  const composerKey = comment.id;
  const draft = commentDrafts[composerKey] ?? '';
  const replyOpen = activeReplyTarget === comment.id;
  const canIndentFurther = depth < MAX_VISUAL_DEPTH;

  return (
    <div className={styles.commentNode}>
      <div className={styles.comment}>
        <div className={styles.commentAvatar} style={{ background: comment.authorColor }}>
          {comment.authorInitials}
        </div>
        <div>
          <div className={styles.commentHead}>
            <span className={styles.commentAuthor}>{comment.authorName}</span>
            <span className={styles.commentRole}>{comment.roleLabel}</span>
            <span className={styles.commentTime}>{comment.timeAgo}</span>
          </div>
          <div className={styles.commentText}>{comment.body}</div>
          <div className={styles.commentActions}>
            {isCommitted ? (
              <button
                type="button"
                className={styles.commentReplyButton}
                onClick={() => onToggleReplyTarget(postId, comment.id)}
              >
                {replyOpen ? 'Cancel' : 'Reply'}
              </button>
            ) : (
              <button type="button" className={styles.commentReplyButton} onClick={onRequestCommit}>
                Commit a slot to reply
              </button>
            )}
          </div>

          {replyOpen && (
            <div className={styles.commentReplyComposer}>
              <input
                type="text"
                className={styles.commentInput}
                placeholder={`Reply to ${comment.authorName}…`}
                value={draft}
                autoFocus
                onChange={(e) => onDraftChange(composerKey, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onSubmitReply(postId, composerKey, comment.id);
                }}
              />
              <button
                type="button"
                className={styles.commentSubmit}
                disabled={commentPosting.has(composerKey) || !draft.trim()}
                onClick={() => onSubmitReply(postId, composerKey, comment.id)}
              >
                {commentPosting.has(composerKey) ? '…' : 'Reply'}
              </button>
            </div>
          )}
          {commentErrors[composerKey] && (
            <div className={styles.composerError}>{commentErrors[composerKey]}</div>
          )}
        </div>
      </div>

      {children.length > 0 && (
        <div className={styles.commentChildren}>
          {children.map((child) => (
            <CommentThreadNode
              key={child.comment.id}
              node={child}
              postId={postId}
              depth={canIndentFurther ? depth + 1 : depth}
              isCommitted={isCommitted}
              activeReplyTarget={activeReplyTarget}
              commentDrafts={commentDrafts}
              commentPosting={commentPosting}
              commentErrors={commentErrors}
              onToggleReplyTarget={onToggleReplyTarget}
              onDraftChange={onDraftChange}
              onSubmitReply={onSubmitReply}
              onRequestCommit={onRequestCommit}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProblemPage() {
  const { problemId } = useParams<{ problemId: string }>();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [feed, setFeed] = useState<FeedPost[]>([]);
  const [lock, setLock] = useState<CommittedProblemSummary | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [showCommit, setShowCommit] = useState(false);

  // Post composer state.
  const [composerBody, setComposerBody] = useState('');
  const [posting, setPosting] = useState(false);
  const [composerError, setComposerError] = useState<string | null>(null);

  // Optimistic local "did I like this" state — the like endpoint only
  // returns the new count, not a boolean, so there's no server truth to
  // sync against. Resets on reload; that's an accepted v1 tradeoff (see
  // feedApi.ts's toggleLike docstring).
  const [likedPostIds, setLikedPostIds] = useState<Set<string>>(new Set());
  const [likeBusyIds, setLikeBusyIds] = useState<Set<string>>(new Set());

  // Comments are fetched lazily per post (on "Reply" expand) rather than
  // eagerly for the whole feed, to avoid an N+1 request storm on load.
  const [expandedPostIds, setExpandedPostIds] = useState<Set<string>>(new Set());
  const [commentsByPost, setCommentsByPost] = useState<Record<string, Comment[]>>({});
  const [commentsLoading, setCommentsLoading] = useState<Set<string>>(new Set());
  // Drafts/posting/errors are keyed by "composer key" — either a post id
  // (the top-level "reply to the post" composer) or a comment id (a
  // per-comment "reply to this comment" composer, issue #98). Both kinds
  // of composer share the same shape, so one set of maps covers both.
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({});
  const [commentPosting, setCommentPosting] = useState<Set<string>>(new Set());
  const [commentErrors, setCommentErrors] = useState<Record<string, string>>({});
  // Which comment (if any) has its reply composer open, per post. null
  // means "no comment-level composer open for this post" (the top-level
  // one under the thread is always available once expanded).
  const [activeReplyTarget, setActiveReplyTarget] = useState<Record<string, string | null>>({});

  // Sort control (issue #98): 'new' (default) or 'top' by like count —
  // no "hot"/time-decayed sort in this pass, see issue for reasoning.
  const [feedSort, setFeedSort] = useState<FeedSort>('new');

  const isCommitted = Boolean(lock);

  // Build each expanded post's comment tree from its flat parent-pointer
  // list only when that post's comments actually change (issue #98) —
  // avoids re-walking every post's thread on unrelated re-renders (e.g.
  // typing in an unrelated composer).
  const commentTreesByPost = useMemo(() => {
    const trees: Record<string, CommentTreeNode[]> = {};
    for (const [postId, comments] of Object.entries(commentsByPost)) {
      trees[postId] = buildCommentTree(comments);
    }
    return trees;
  }, [commentsByPost]);

  const load = useCallback(
    async (sort: FeedSort = feedSort) => {
      if (!problemId) return;
      const [p, t, f, committed] = await Promise.all([
        problemsPort.getById(problemId),
        problemsPort.getTasks(problemId),
        problemsPort.getFeed(problemId, sort),
        currentUserPort.getCommittedProblems(),
      ]);
      setProblem(p);
      setTasks(t);
      setFeed(f);
      setLock(committed.find((c) => c.problemId === problemId) ?? null);
      setLoaded(true);
    },
    [problemId, feedSort],
  );

  useEffect(() => {
    let cancelled = false;
    load().catch(() => {
      if (!cancelled) setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problemId]);

  async function handleChangeSort(sort: FeedSort) {
    if (sort === feedSort || !problemId) return;
    setFeedSort(sort);
    try {
      const f = await problemsPort.getFeed(problemId, sort);
      setFeed(f);
    } catch {
      // Non-critical — keep the previous ordering on failure.
    }
  }

  async function handleCreatePost() {
    if (!problemId || !composerBody.trim()) return;
    setPosting(true);
    setComposerError(null);
    try {
      const post = await feedApi.createPost(problemId, composerBody.trim());
      setFeed((prev) => [post, ...prev]);
      setComposerBody('');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not post. Please try again.';
      setComposerError(message);
    } finally {
      setPosting(false);
    }
  }

  async function handleToggleLike(postId: string) {
    if (!problemId || likeBusyIds.has(postId)) return;
    setLikeBusyIds((prev) => new Set(prev).add(postId));
    try {
      const { likeCount } = await feedApi.toggleLike(problemId, postId);
      setFeed((prev) => prev.map((p) => (p.id === postId ? { ...p, likeCount } : p)));
      setLikedPostIds((prev) => {
        const next = new Set(prev);
        if (next.has(postId)) {
          next.delete(postId);
        } else {
          next.add(postId);
        }
        return next;
      });
    } catch {
      // Non-critical — leave the count as-is; the user can retry the click.
    } finally {
      setLikeBusyIds((prev) => {
        const next = new Set(prev);
        next.delete(postId);
        return next;
      });
    }
  }

  async function handleToggleReply(postId: string) {
    const alreadyExpanded = expandedPostIds.has(postId);
    setExpandedPostIds((prev) => {
      const next = new Set(prev);
      if (alreadyExpanded) {
        next.delete(postId);
      } else {
        next.add(postId);
      }
      return next;
    });
    if (alreadyExpanded || !problemId || commentsByPost[postId]) return;

    setCommentsLoading((prev) => new Set(prev).add(postId));
    try {
      const comments = await feedApi.getComments(problemId, postId);
      setCommentsByPost((prev) => ({ ...prev, [postId]: comments }));
    } catch {
      setCommentsByPost((prev) => ({ ...prev, [postId]: [] }));
    } finally {
      setCommentsLoading((prev) => {
        const next = new Set(prev);
        next.delete(postId);
        return next;
      });
    }
  }

  /**
   * `composerKey` is the drafts/posting/errors map key: the post id for
   * the top-level "reply to the post" composer, or a comment id for a
   * per-comment "reply to this comment" composer (issue #98).
   * `parentCommentId` is what actually gets sent to the API — null for
   * a top-level reply, the target comment's id otherwise.
   */
  async function handleCreateComment(postId: string, composerKey: string, parentCommentId: string | null) {
    const draft = (commentDrafts[composerKey] ?? '').trim();
    if (!problemId || !draft) return;
    setCommentPosting((prev) => new Set(prev).add(composerKey));
    setCommentErrors((prev) => ({ ...prev, [composerKey]: '' }));
    try {
      const comment = await feedApi.createComment(problemId, postId, draft, parentCommentId);
      setCommentsByPost((prev) => ({ ...prev, [postId]: [...(prev[postId] ?? []), comment] }));
      setCommentDrafts((prev) => ({ ...prev, [composerKey]: '' }));
      if (parentCommentId) {
        // Reply landed — close that comment's reply composer.
        setActiveReplyTarget((prev) => ({ ...prev, [postId]: null }));
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not comment. Please try again.';
      setCommentErrors((prev) => ({ ...prev, [composerKey]: message }));
    } finally {
      setCommentPosting((prev) => {
        const next = new Set(prev);
        next.delete(composerKey);
        return next;
      });
    }
  }

  function handleToggleReplyTarget(postId: string, commentId: string) {
    setActiveReplyTarget((prev) => ({
      ...prev,
      [postId]: prev[postId] === commentId ? null : commentId,
    }));
  }

  function handleCommentDraftChange(composerKey: string, value: string) {
    setCommentDrafts((prev) => ({ ...prev, [composerKey]: value }));
  }

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
            <Link to={`/graph/${problem.id}`}>
              <Button variant="secondary">Graph</Button>
            </Link>
            <Link to={`/coordinator/${problem.id}`}>
              <Button variant="secondary">Coordinator</Button>
            </Link>
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

          {isCommitted ? (
            <div className={styles.composer}>
              <textarea
                className={styles.composerInput}
                placeholder="Post an update to committed members…"
                value={composerBody}
                onChange={(e) => setComposerBody(e.target.value)}
                rows={3}
              />
              {composerError && <div className={styles.composerError}>{composerError}</div>}
              <div className={styles.composerActions}>
                <Button
                  variant="primary"
                  type="button"
                  disabled={posting || !composerBody.trim()}
                  onClick={handleCreatePost}
                >
                  {posting ? 'Posting…' : 'Post'}
                </Button>
              </div>
            </div>
          ) : (
            <div className={styles.gateNotice}>
              <span>🔒</span>
              <span className={styles.gateText}>
                Only committed members can post here.{' '}
                <button type="button" className={styles.gateLink} onClick={() => setShowCommit(true)}>
                  Commit a slot to join the discussion.
                </button>
              </span>
            </div>
          )}

          <div className={styles.sortRow}>
            <span className={styles.sortLabel}>Sort</span>
            <button
              type="button"
              className={`${styles.sortButton} ${feedSort === 'new' ? styles.sortButtonActive : ''}`}
              onClick={() => handleChangeSort('new')}
            >
              New
            </button>
            <button
              type="button"
              className={`${styles.sortButton} ${feedSort === 'top' ? styles.sortButtonActive : ''}`}
              onClick={() => handleChangeSort('top')}
            >
              Top
            </button>
          </div>

          <div className={styles.posts}>
            {feed.map((post) => {
              const liked = likedPostIds.has(post.id);
              const expanded = expandedPostIds.has(post.id);
              const comments = commentsByPost[post.id];
              const commentTree = commentTreesByPost[post.id] ?? [];
              const draft = commentDrafts[post.id] ?? '';
              return (
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
                        <button
                          type="button"
                          className={`${styles.likeButton} ${liked ? styles.likeButtonActive : ''}`}
                          onClick={() => handleToggleLike(post.id)}
                          disabled={!isCommitted || likeBusyIds.has(post.id)}
                          title={isCommitted ? undefined : 'Only committed members can like posts here.'}
                        >
                          ♥ {post.likeCount}
                        </button>
                        <button type="button" className={styles.replyButton} onClick={() => handleToggleReply(post.id)}>
                          Reply{expanded ? ' ▲' : ' ▾'}
                        </button>
                      </div>
                    )}

                    {expanded && (
                      <div className={styles.commentThread}>
                        {commentsLoading.has(post.id) && <div className={styles.commentLoading}>Loading comments…</div>}
                        {!commentsLoading.has(post.id) && comments && comments.length === 0 && (
                          <div className={styles.commentEmpty}>No comments yet.</div>
                        )}
                        {commentTree.map((node) => (
                          <CommentThreadNode
                            key={node.comment.id}
                            node={node}
                            postId={post.id}
                            depth={0}
                            isCommitted={isCommitted}
                            activeReplyTarget={activeReplyTarget[post.id] ?? null}
                            commentDrafts={commentDrafts}
                            commentPosting={commentPosting}
                            commentErrors={commentErrors}
                            onToggleReplyTarget={handleToggleReplyTarget}
                            onDraftChange={handleCommentDraftChange}
                            onSubmitReply={(pId, key, parentId) => handleCreateComment(pId, key, parentId)}
                            onRequestCommit={() => setShowCommit(true)}
                          />
                        ))}

                        {isCommitted ? (
                          <div className={styles.commentComposer}>
                            <input
                              type="text"
                              className={styles.commentInput}
                              placeholder="Write a comment…"
                              value={draft}
                              onChange={(e) => handleCommentDraftChange(post.id, e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleCreateComment(post.id, post.id, null);
                              }}
                            />
                            <button
                              type="button"
                              className={styles.commentSubmit}
                              disabled={commentPosting.has(post.id) || !draft.trim()}
                              onClick={() => handleCreateComment(post.id, post.id, null)}
                            >
                              {commentPosting.has(post.id) ? '…' : 'Reply'}
                            </button>
                          </div>
                        ) : (
                          <div className={styles.commentGate}>
                            <button type="button" className={styles.gateLink} onClick={() => setShowCommit(true)}>
                              Commit a slot to comment.
                            </button>
                          </div>
                        )}
                        {commentErrors[post.id] && <div className={styles.composerError}>{commentErrors[post.id]}</div>}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
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

          <Link to={`/coordinator/${problem.id}`} className={styles.invokeButton}>
            ✦ Invoke coordinator
          </Link>
        </div>
      </div>

      {showCommit && (
        <Modal onClose={() => setShowCommit(false)} titleId="commit-modal-title">
          <CommitModal problem={problem} onClose={() => setShowCommit(false)} onCommitted={load} />
        </Modal>
      )}
    </div>
  );
}
