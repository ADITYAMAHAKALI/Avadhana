import { MockCurrentUserPort } from './mock/MockCurrentUserPort';
import { MockModerationPort } from './mock/MockModerationPort';
import { MockProblemsPort } from './mock/MockProblemsPort';

/**
 * Composition root. Every screen imports its data from here, never
 * directly from a mock/* file — swapping to a real HTTP-backed
 * implementation (once services/backend-api grows domain endpoints,
 * see issues #4-17) means changing only this file.
 */
export const currentUserPort = new MockCurrentUserPort();
export const problemsPort = new MockProblemsPort();
export const moderationPort = new MockModerationPort();
