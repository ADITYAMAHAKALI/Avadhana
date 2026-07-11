export type Tier = 'S' | 'A' | 'B' | 'C' | 'D';

export type Role = 'thinker' | 'actor' | 'backer';

export type ActorSpecialization =
  | 'Legal'
  | 'Research'
  | 'Content'
  | 'Web & app dev'
  | 'Ad campaign'
  | 'Field organizing';

export type CommitmentStatus = 'active' | 'resolved' | 'continued' | 'abandoned';

/**
 * Problem-level AGGREGATE resolution status (issue #100) — computed
 * server-side from committed members' individual checkpoints, never
 * set directly. See backend's
 * app/services/problem_lifecycle_service.py for the full computation:
 *   - open: below the resolved-claim threshold.
 *   - pending_resolution: threshold met, 7-day objection window still open, no objection yet.
 *   - resolved: threshold met, window closed (or still open) with zero objections.
 *   - disputed: threshold met, at least one committed member objected inside the window.
 */
export type ProblemLifecycleStatus = 'open' | 'pending_resolution' | 'resolved' | 'disputed';

export interface User {
  id: string;
  name: string;
  initials: string;
  location: string;
  memberSince: string;
  reputation: number;
  avatarColor: string;
}

export interface FocusSlot {
  index: number;
  occupied: boolean;
  problemId: string | null;
}

export interface CommittedProblemSummary {
  problemId: string;
  role: Role;
  specialization: ActorSpecialization | null;
  dayInCycle: number;
  cycleLengthDays: number;
  nextTask: string | null;
}

export interface CommitmentHistoryEntry {
  problemTitle: string;
  role: Role;
  status: CommitmentStatus;
  note: string;
}

export interface Problem {
  id: string;
  title: string;
  summary: string;
  location: string;
  category: string;
  tier: Tier;
  createdAt: string;
  parentProblemTitle: string | null;
  thinkerCount: number;
  actorCount: number;
  backerCount: number;
  followingCount: number;
  // --- Resolution status (issue #100) — computed server-side, read-only ---
  resolutionStatus: ProblemLifecycleStatus;
  resolvedCount: number;
  totalCommitted: number;
  /** null when the threshold is unreachable (fewer than 2 currently-committed members). */
  resolutionThreshold: number | null;
  /** null when there's no active/past resolution window (status === 'open'). */
  resolutionWindowEndsAt: string | null;
  objectionCount: number;
}

export interface TaskItem {
  id: string;
  label: string;
  status: 'done' | 'open' | 'unclaimed';
  assignee: string | null;
}

export interface PollOption {
  label: string;
  percent: number;
}

export interface Poll {
  question: string;
  options: PollOption[];
  committedVoters: number;
  closesInDays: number;
}

export interface FeedPost {
  id: string;
  authorInitials: string;
  authorName: string;
  authorColor: string;
  roleLabel: string;
  timeAgo: string;
  body: string;
  likeCount: number;
  poll?: Poll;
}

export interface Comment {
  id: string;
  postId: string;
  authorInitials: string;
  authorName: string;
  authorColor: string;
  roleLabel: string;
  timeAgo: string;
  body: string;
}

export interface ModerationQueueItem {
  id: string;
  status: 'flagged' | 'auto-blocked';
  confidence: number;
  timeAgo: string;
  body: string;
  author: string;
  authorNote: string;
  appealFiled: boolean;
}

export interface InvocationLogEntry {
  id: string;
  type: string;
  timeAgo: string;
  detail: string;
}

export interface ProblemGraphNode {
  id: string;
  tier: Tier;
  title: string;
  note: string;
  highlighted?: boolean;
  isMerge?: boolean;
  x: number;
  y: number;
}

export interface ProblemGraphEdge {
  fromId: string;
  toId: string;
  kind: 'split' | 'merge';
}
