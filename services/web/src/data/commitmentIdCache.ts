/**
 * Frontend-only cache mapping problemId -> commitmentId, keyed in
 * localStorage. Exists to bridge a real gap in the current API contract:
 * `GET /users/me/committed-problems` (used by DashboardPage/ProblemPage to
 * render the viewer's active commitments) returns `problemId` but not
 * `commitmentId`, while `POST /commitments/{commitmentId}/checkpoint` (the
 * 90-day checkpoint action) is keyed by commitment id, not problem id.
 * There is no backend endpoint to look up a commitment id from a problem id
 * for the current user, and this pass is frontend-only (see build brief) so
 * we can't add one.
 *
 * Workaround: `POST /problems/{problemId}/commitments` (already called from
 * CommitModal) returns the created commitment's id — we stash it here the
 * moment a commitment succeeds, so the checkpoint flow can look it up later
 * by problem id. This only covers commitments made after this cache
 * existed / in this browser; see CheckpointModal's handling of a cache miss
 * for the fallback UX.
 */
const STORAGE_KEY = 'avadhana_commitment_ids';

function readMap(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

function writeMap(map: Record<string, string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Best-effort only — localStorage can throw in private-browsing/quota
    // edge cases. The checkpoint flow degrades gracefully on a cache miss.
  }
}

export function rememberCommitmentId(problemId: string, commitmentId: string): void {
  const map = readMap();
  map[problemId] = commitmentId;
  writeMap(map);
}

export function getCommitmentId(problemId: string): string | null {
  return readMap()[problemId] ?? null;
}
