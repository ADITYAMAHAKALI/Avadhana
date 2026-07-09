import { MockCurrentUserPort } from './mock/MockCurrentUserPort';
import { MockModerationPort } from './mock/MockModerationPort';
import { MockProblemsPort } from './mock/MockProblemsPort';
import { RealCurrentUserPort } from './real/RealCurrentUserPort';
import { RealProblemsPort } from './real/RealProblemsPort';

/**
 * Composition root. Every screen imports its data from here, never
 * directly from a mock/* or real/* file — this is the only place that
 * decides which implementation is live.
 *
 * Toggle: real ports are used when VITE_API_BASE_URL is set AND
 * VITE_USE_MOCK_DATA is not "true". Concretely:
 *   - No .env at all (default)      -> mock data (today's behavior, unchanged)
 *   - VITE_API_BASE_URL set         -> real HTTP ports against that backend
 *   - VITE_API_BASE_URL set AND
 *     VITE_USE_MOCK_DATA=true       -> mock data anyway (explicit override)
 *
 * This keeps `npm run dev` working out of the box with no backend running,
 * while making it a one-line .env change to point the app at a live server.
 * See services/web/README.md and .env.example for setup.
 *
 * ModerationPort has no backend yet (AI moderation is out of scope for this
 * pass) and stays mock-only regardless of the toggle.
 */
const hasApiBaseUrl = Boolean(import.meta.env.VITE_API_BASE_URL);
const forceMock = import.meta.env.VITE_USE_MOCK_DATA === 'true';
const useReal = hasApiBaseUrl && !forceMock;

export const currentUserPort = useReal ? new RealCurrentUserPort() : new MockCurrentUserPort();
export const problemsPort = useReal ? new RealProblemsPort() : new MockProblemsPort();
export const moderationPort = new MockModerationPort();

/**
 * Exported so standalone write-action modules (e.g. the problem-creation
 * screen) can pick real vs. mock behavior without re-deriving the env-var
 * toggle themselves. Additive — doesn't change any existing export above.
 */
export const isUsingRealData = useReal;
