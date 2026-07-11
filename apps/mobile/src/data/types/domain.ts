/**
 * Mirrors services/web/src/types/domain.ts — same backend, same JSON shapes.
 * Trimmed to what the mobile screens built so far actually use; add fields
 * here as more of the web app's routes get a mobile equivalent.
 */

export type Tier = 'S' | 'A' | 'B' | 'C' | 'D';

export type Role = 'thinker' | 'actor' | 'backer';

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

export interface CommittedProblemSummary {
  problemId: string;
  role: Role;
  specialization: string | null;
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
  thinkerCount: number;
  actorCount: number;
  backerCount: number;
  followingCount: number;
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
}
