import type { ModerationPort } from '../interfaces';
import { INVOCATION_LOG_BY_PROBLEM, MODERATION_QUEUE_BY_PROBLEM } from './fixtures';

export class MockModerationPort implements ModerationPort {
  async getQueue(problemId: string) {
    return MODERATION_QUEUE_BY_PROBLEM[problemId] ?? [];
  }

  async getInvocationLog(problemId: string) {
    return INVOCATION_LOG_BY_PROBLEM[problemId] ?? [];
  }

  async getStats(problemId: string) {
    const queue = MODERATION_QUEUE_BY_PROBLEM[problemId] ?? [];
    return {
      autoBlocked: queue.filter((q) => q.status === 'auto-blocked').length,
      flagged: queue.filter((q) => q.status === 'flagged').length,
      openAppeals: queue.filter((q) => q.appealFiled).length,
    };
  }
}
