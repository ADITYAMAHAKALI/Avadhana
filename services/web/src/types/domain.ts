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
