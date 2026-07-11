import type {
  CommitmentHistoryEntry,
  CommittedProblemSummary,
  FeedPost,
  FeedSort,
  InvocationLogEntry,
  ModerationQueueItem,
  Problem,
  ProblemGraphEdge,
  ProblemGraphNode,
  TaskItem,
  User,
} from '../types/domain';

/**
 * Ports the screens depend on. Today only mock implementations exist
 * (services/backend-api has no domain endpoints yet — see issues #4-17).
 * Swap in a real HTTP-backed implementation later without touching any
 * screen component.
 */
export interface CurrentUserPort {
  getCurrentUser(): Promise<User>;
  getFocusSlotCount(): Promise<{ used: number; total: number }>;
  getCommittedProblems(): Promise<CommittedProblemSummary[]>;
  getCommitmentHistory(): Promise<CommitmentHistoryEntry[]>;
}

/** Optional discovery filters — mirrors the backend's GET /problems query params (q/tier/location/category), all optional. */
export interface DiscoverFilters {
  q?: string;
  tier?: string;
  location?: string;
  category?: string;
}

export interface ProblemsPort {
  listDiscoverable(filters?: DiscoverFilters): Promise<Problem[]>;
  getById(problemId: string): Promise<Problem | null>;
  getTasks(problemId: string): Promise<TaskItem[]>;
  /** `sort` (issue #98): 'new' (default, created_at desc) or 'top' (like_count desc). */
  getFeed(problemId: string, sort?: FeedSort): Promise<FeedPost[]>;
  getGraph(problemId: string): Promise<{ nodes: ProblemGraphNode[]; edges: ProblemGraphEdge[] }>;
}

export interface ModerationPort {
  getQueue(problemId: string): Promise<ModerationQueueItem[]>;
  getInvocationLog(problemId: string): Promise<InvocationLogEntry[]>;
  getStats(problemId: string): Promise<{ autoBlocked: number; flagged: number; openAppeals: number }>;
}
