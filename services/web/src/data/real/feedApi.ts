import type { Comment, FeedPost } from '../../types/domain';
import { CURRENT_USER, COMMENTS_BY_POST, FEED_BY_PROBLEM } from '../mock/fixtures';
import { apiFetch } from './httpClient';

/**
 * Feed write actions (post/like/comment) live here as a standalone module,
 * the same convention commitmentsApi.ts and authApi.ts follow — ProblemsPort
 * is deliberately read-only (see its docstring in ../interfaces.ts), so
 * writes never got added to that interface.
 *
 * Mirrors data/index.ts's real-vs-mock toggle (VITE_API_BASE_URL /
 * VITE_USE_MOCK_DATA) at the call-site level rather than through a port,
 * since ProblemsPort has no place for these methods. In mock mode, calls
 * mutate the same in-memory fixtures MockProblemsPort reads from, so a
 * composer/like/comment submitted against mock data is reflected back on
 * next read (until page reload — fixtures are in-memory only).
 */
const hasApiBaseUrl = Boolean(import.meta.env.VITE_API_BASE_URL);
const forceMock = import.meta.env.VITE_USE_MOCK_DATA === 'true';
const useReal = hasApiBaseUrl && !forceMock;

function mockId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

export const feedApi = {
  async createPost(problemId: string, body: string): Promise<FeedPost> {
    if (!useReal) {
      const post: FeedPost = {
        id: mockId('f'),
        authorInitials: CURRENT_USER.initials,
        authorName: CURRENT_USER.name,
        authorColor: CURRENT_USER.avatarColor,
        roleLabel: 'Committed member',
        timeAgo: 'just now',
        body,
        likeCount: 0,
      };
      const existing = FEED_BY_PROBLEM[problemId] ?? [];
      FEED_BY_PROBLEM[problemId] = [post, ...existing];
      return post;
    }
    return apiFetch<FeedPost>(`/problems/${problemId}/posts`, { method: 'POST', body: { body } });
  },

  /**
   * Toggle-like a post. Backend only returns the new count, not a "did I
   * like it" flag — callers track liked/unliked state locally (see
   * ProblemPage's `likedPostIds` state) and just trust their own optimistic
   * toggle, resetting on reload. In mock mode, mutates FEED_BY_PROBLEM's
   * matching post in place so the count persists across a re-fetch within
   * the session.
   */
  async toggleLike(problemId: string, postId: string): Promise<{ likeCount: number }> {
    if (!useReal) {
      const posts = FEED_BY_PROBLEM[problemId] ?? [];
      const post = posts.find((p) => p.id === postId);
      if (!post) return { likeCount: 0 };
      // Mock has no persisted "did I like" state either — approximate a toggle
      // by nudging the count; good enough for local dev without a backend.
      post.likeCount = post.likeCount > 0 ? post.likeCount - 1 : post.likeCount + 1;
      return { likeCount: post.likeCount };
    }
    return apiFetch<{ likeCount: number }>(`/problems/${problemId}/posts/${postId}/like`, { method: 'POST' });
  },

  async createComment(problemId: string, postId: string, body: string): Promise<Comment> {
    if (!useReal) {
      const comment: Comment = {
        id: mockId('c'),
        postId,
        authorInitials: CURRENT_USER.initials,
        authorName: CURRENT_USER.name,
        authorColor: CURRENT_USER.avatarColor,
        roleLabel: 'Committed member',
        timeAgo: 'just now',
        body,
      };
      const existing = COMMENTS_BY_POST[postId] ?? [];
      COMMENTS_BY_POST[postId] = [...existing, comment];
      return comment;
    }
    return apiFetch<Comment>(`/problems/${problemId}/posts/${postId}/comments`, { method: 'POST', body: { body } });
  },

  async getComments(problemId: string, postId: string): Promise<Comment[]> {
    if (!useReal) {
      return COMMENTS_BY_POST[postId] ?? [];
    }
    return apiFetch<Comment[]>(`/problems/${problemId}/posts/${postId}/comments`, { auth: false });
  },
};
