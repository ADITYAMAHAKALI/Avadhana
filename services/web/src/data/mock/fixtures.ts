import type {
  Comment,
  CommitmentHistoryEntry,
  CommittedProblemSummary,
  FeedPost,
  InvocationLogEntry,
  ModerationQueueItem,
  Problem,
  ProblemGraphEdge,
  ProblemGraphNode,
  TaskItem,
  User,
} from '../../types/domain';

export const CURRENT_USER: User = {
  id: 'u-ravi',
  name: 'Ravi Menon',
  initials: 'RM',
  location: 'Pune, MH',
  memberSince: 'Jan 2026',
  reputation: 128,
  avatarColor: 'var(--color-gold-accent)',
};

export const PROBLEMS: Problem[] = [
  {
    id: 'p-groundwater',
    title: 'Groundwater contamination near Govindpura',
    summary: 'Industrial runoff suspected in 3 wards. Needs on-ground water sampling and an RTI trail.',
    location: 'Bhopal, MP',
    category: 'Environment',
    tier: 'A',
    createdAt: '12 Apr 2026',
    parentProblemTitle: 'Water safety, Bhopal district',
    thinkerCount: 5,
    actorCount: 2,
    backerCount: 1,
    followingCount: 61,
    resolutionStatus: 'open',
    resolvedCount: 0,
    totalCommitted: 8,
    resolutionThreshold: 2,
    resolutionWindowEndsAt: null,
    objectionCount: 0,
  },
  {
    id: 'p-crossing',
    title: 'Unsafe pedestrian crossing at Kothrud school',
    summary: 'No signal or speed-breaker outside a 900-student school. Two near-misses this term.',
    location: 'Pune, MH',
    category: 'Safety',
    tier: 'B',
    createdAt: '2 Feb 2026',
    parentProblemTitle: null,
    thinkerCount: 3,
    actorCount: 4,
    backerCount: 2,
    followingCount: 38,
    // Illustrative "pending_resolution" example for mock mode: 2 of 9
    // committed members have claimed resolved, window still open.
    resolutionStatus: 'pending_resolution',
    resolvedCount: 2,
    totalCommitted: 9,
    resolutionThreshold: 2,
    resolutionWindowEndsAt: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000).toISOString(),
    objectionCount: 0,
  },
  {
    id: 'p-watertesting',
    title: "Municipal water-testing data isn't public by default",
    summary: 'A push to mandate open publication of ward-level water quality results across state boards.',
    location: 'Nationwide',
    category: 'Policy',
    tier: 'S',
    createdAt: '3 Jan 2026',
    parentProblemTitle: null,
    thinkerCount: 12,
    actorCount: 7,
    backerCount: 3,
    followingCount: 214,
    resolutionStatus: 'open',
    resolvedCount: 0,
    totalCommitted: 22,
    resolutionThreshold: 2,
    resolutionWindowEndsAt: null,
    objectionCount: 0,
  },
  {
    id: 'p-ramp',
    title: 'Broken ramp blocks wheelchair access to PHC',
    summary: 'A single afternoon of masonry and one RTI would likely fix this. Low-resource win.',
    location: 'Nagpur, MH',
    category: 'Access',
    tier: 'D',
    createdAt: '20 Jun 2026',
    parentProblemTitle: null,
    thinkerCount: 1,
    actorCount: 1,
    backerCount: 0,
    followingCount: 9,
    // Only 2 committed members total — right at the threshold floor.
    resolutionStatus: 'resolved',
    resolvedCount: 2,
    totalCommitted: 2,
    resolutionThreshold: 2,
    resolutionWindowEndsAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    objectionCount: 0,
  },
  {
    id: 'p-sensors',
    title: 'Standardizing calibration for a citizen air-quality sensor network',
    summary: 'Not civic in the usual sense — a research problem. 40 low-cost sensors drift out of calibration within weeks; needs a shared protocol and a paper.',
    location: 'Bengaluru, KA',
    category: 'Science',
    tier: 'B',
    createdAt: '15 May 2026',
    parentProblemTitle: null,
    thinkerCount: 9,
    actorCount: 2,
    backerCount: 0,
    followingCount: 27,
    // Illustrative "disputed" example: threshold met but a member objected.
    resolutionStatus: 'disputed',
    resolvedCount: 2,
    totalCommitted: 11,
    resolutionThreshold: 2,
    resolutionWindowEndsAt: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    objectionCount: 1,
  },
];

export const COMMITTED_PROBLEMS: CommittedProblemSummary[] = [
  {
    problemId: 'p-groundwater',
    role: 'thinker',
    specialization: null,
    dayInCycle: 86,
    cycleLengthDays: 90,
    nextTask: 'Draft RTI on water-board test logs',
  },
  {
    problemId: 'p-crossing',
    role: 'actor',
    specialization: null,
    dayInCycle: 43,
    cycleLengthDays: 90,
    nextTask: 'Meet ward officer re: signal timing',
  },
];

export const COMMITMENT_HISTORY: CommitmentHistoryEntry[] = [
  {
    problemTitle: 'Streetlight blackout, Baner Rd',
    role: 'actor',
    status: 'resolved',
    note: 'Completed full 90-day cycle',
  },
  {
    problemTitle: 'School library fund, Wagholi',
    role: 'backer',
    status: 'continued',
    note: 'Continued a second cycle',
  },
  {
    problemTitle: 'Ward waste segregation drive',
    role: 'actor',
    status: 'abandoned',
    note: 'Abandoned before the 90-day minimum',
  },
];

export const TASKS_BY_PROBLEM: Record<string, TaskItem[]> = {
  'p-groundwater': [
    { id: 't1', label: 'Collect borewell readings (3 sites)', status: 'done', assignee: null },
    { id: 't2', label: 'Draft RTI on water-board logs', status: 'open', assignee: 'you' },
    { id: 't3', label: 'Ward officer meeting', status: 'open', assignee: 'Anita' },
    { id: 't4', label: 'Fund lab re-test ₹18k', status: 'unclaimed', assignee: null },
  ],
};

export const FEED_BY_PROBLEM: Record<string, FeedPost[]> = {
  'p-groundwater': [
    {
      id: 'f1',
      authorInitials: 'AS',
      authorName: 'Anita Shah',
      authorColor: 'var(--color-actor)',
      roleLabel: 'Actor · Legal',
      timeAgo: '2h',
      body: "Water-board office confirmed a meeting Thursday 11am. I'll bring the borewell readings. If anyone has the 2024 sampling PDF, upload it to Assets.",
      likeCount: 6,
    },
    {
      id: 'f2',
      authorInitials: 'RM',
      authorName: 'Ravi Menon',
      authorColor: 'var(--color-thinker)',
      roleLabel: 'Thinker',
      timeAgo: '5h',
      body: 'Poll — where do committed members want to escalate first?',
      likeCount: 0,
      poll: {
        question: 'Where do committed members want to escalate first?',
        options: [
          { label: 'RTI on water board logs', percent: 62 },
          { label: 'Independent lab re-test', percent: 26 },
          { label: 'Press / local media', percent: 12 },
        ],
        committedVoters: 8,
        closesInDays: 2,
      },
    },
  ],
};

/**
 * Comments keyed by post id. The mock feedApi
 * (services/web/src/data/real/feedApi.ts's mock-mode branch) pushes into
 * these arrays at runtime so posting/commenting/liking "work" against
 * mock data without a backend. Not persisted across a page reload.
 *
 * Post f1 is seeded with a small thread (issue #98) — a top-level
 * comment, a reply to it, and a reply-to-that-reply — so nested/threaded
 * rendering (`buildCommentTree` in ProblemPage.tsx) is actually exercised
 * in mock mode, not just against a live backend.
 */
export const COMMENTS_BY_POST: Record<string, Comment[]> = {
  f1: [
    {
      id: 'c1',
      postId: 'f1',
      parentCommentId: null,
      authorInitials: 'DK',
      authorName: 'Divya Kulkarni',
      authorColor: 'var(--color-backer)',
      roleLabel: 'Backer',
      timeAgo: '1h',
      body: 'I can cover the lab re-test cost if it comes to that — let me know once the ward officer meeting happens.',
    },
    {
      id: 'c2',
      postId: 'f1',
      parentCommentId: 'c1',
      authorInitials: 'AS',
      authorName: 'Anita Shah',
      authorColor: 'var(--color-actor)',
      roleLabel: 'Actor · Legal',
      timeAgo: '45m',
      body: 'Appreciated — will report back right after Thursday. Might not need it if the RTI response is enough on its own.',
    },
    {
      id: 'c3',
      postId: 'f1',
      parentCommentId: 'c2',
      authorInitials: 'RM',
      authorName: 'Ravi Menon',
      authorColor: 'var(--color-thinker)',
      roleLabel: 'Thinker',
      timeAgo: '30m',
      body: "Agreed, let's hold off on the re-test ask until we see what the RTI turns up.",
    },
  ],
};

export const GRAPH_BY_PROBLEM: Record<
  string,
  { nodes: ProblemGraphNode[]; edges: ProblemGraphEdge[] }
> = {
  'p-groundwater': {
    nodes: [
      { id: 'root', tier: 'S', title: 'Water safety, Bhopal district', note: 'root · created Jan 2026', x: 40, y: 44 },
      { id: 'p-groundwater', tier: 'A', title: 'Groundwater contamination, Govindpura', note: "you're here · split Apr 2026", highlighted: true, x: 200, y: 124 },
      { id: 'p-surface', tier: 'A', title: 'Surface water pollution, Kolar', note: 'split Apr 2026', x: 200, y: 294 },
      { id: 'p-rti', tier: 'B', title: 'RTI transparency track', note: 'sub-problem', x: 400, y: 64 },
      { id: 'p-industrial', tier: 'B', title: 'Industrial runoff tracing', note: 'sub-problem', x: 400, y: 194 },
      { id: 'p-merge', tier: 'A', title: 'Unified water accountability initiative', note: '1 conflict resolved by moderator', isMerge: true, x: 640, y: 124 },
    ],
    edges: [
      { fromId: 'root', toId: 'p-groundwater', kind: 'split' },
      { fromId: 'root', toId: 'p-surface', kind: 'split' },
      { fromId: 'p-groundwater', toId: 'p-rti', kind: 'split' },
      { fromId: 'p-groundwater', toId: 'p-industrial', kind: 'split' },
      { fromId: 'p-rti', toId: 'p-merge', kind: 'merge' },
      { fromId: 'p-industrial', toId: 'p-merge', kind: 'merge' },
    ],
  },
};

export const MODERATION_QUEUE_BY_PROBLEM: Record<string, ModerationQueueItem[]> = {
  'p-groundwater': [
    {
      id: 'm1',
      status: 'flagged',
      confidence: 0.61,
      timeAgo: '18m ago',
      body: 'Unrelated — has anyone here dealt with property tax appeals in Indore? Different issue but need help.',
      author: 'Deepak K',
      authorNote: 'Thinker · this problem',
      appealFiled: false,
    },
    {
      id: 'm2',
      status: 'auto-blocked',
      confidence: 0.93,
      timeAgo: '1h ago',
      body: 'Buy cheap solar panels DM me 🔥🔥 best price guaranteed',
      author: 'unknown_user',
      authorNote: 'not committed',
      appealFiled: true,
    },
  ],
};

export const INVOCATION_LOG_BY_PROBLEM: Record<string, InvocationLogEntry[]> = {
  'p-groundwater': [
    { id: 'i1', type: 'Summarize', timeAgo: '3h ago', detail: 'Scheduled · 412 tokens · ok' },
    { id: 'i2', type: 'Off-topic scan', timeAgo: '3h ago', detail: '2 blocked · 3 flagged' },
    { id: 'i3', type: 'Checklist gen', timeAgo: '1d ago', detail: 'Manual · Ravi M · 6 items' },
    { id: 'i4', type: 'Summarize', timeAgo: '1d ago', detail: 'Scheduled · 388 tokens · ok' },
  ],
};
