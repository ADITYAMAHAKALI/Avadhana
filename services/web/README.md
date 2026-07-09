# Avadhana Web

React + TypeScript + Vite frontend, ported from the Claude Design mockup `Avadhana Web.dc.html`
(project `01cd5424-5c22-455d-b4d5-657917bb8ffd`).

## Screens

Dashboard (`/dashboard`), Discover (`/discover`), Problem workspace (`/problems/:problemId`),
Problem graph (`/graph/:problemId`), Profile (`/profile`), Coordinator & moderation
(`/coordinator/:problemId`), Login (`/login`), Signup (`/signup`).

## Architecture

- **Design tokens**: `src/styles/tokens.css` — CSS custom properties sourced from the "Avadhana
  Design System" Claude Design project. Keep in sync if the design system changes.
- **Data layer**: `src/data/interfaces.ts` defines ports (`CurrentUserPort`, `ProblemsPort`,
  `ModerationPort`). Two implementations exist:
  - `src/data/mock/` — fixture-backed, matching the design mockup's example content.
  - `src/data/real/` — HTTP-backed (`RealCurrentUserPort`, `RealProblemsPort`), calling
    `services/backend-api` per its documented contract. `ModerationPort` has no real
    implementation yet (AI moderation is out of scope for this pass) and stays mock-only.

  `src/data/index.ts` is the composition root and the **only** file that decides which
  implementation is live — no screen component imports from `mock/` or `real/` directly.

  **Mock vs. real toggle**: controlled by env vars read at build/dev time (see `.env.example`):
  - No `VITE_API_BASE_URL` set (default) → mock data. `npm run dev` always works with zero setup.
  - `VITE_API_BASE_URL` set → real ports call that backend.
  - `VITE_API_BASE_URL` set **and** `VITE_USE_MOCK_DATA=true` → mock data anyway (explicit override).

- **HTTP client**: `src/data/real/httpClient.ts` — shared `fetch` wrapper: base URL from
  `VITE_API_BASE_URL`, attaches `Authorization: Bearer <token>` from `localStorage`
  (key `avadhana_token`), parses the backend's `{error, message}` error shape into a typed
  `ApiError` (with `.status`/`.code`/`.message`), and on any `401` clears the stored token and
  fires a registered "session expired" callback (wired by `AuthContext`) so the whole app drops
  back to logged-out state.
- **Auth**: `src/context/AuthContext.tsx` calls `src/data/real/authApi.ts` (`POST /auth/login`,
  `POST /auth/signup`) when real ports are active; in mock mode it still just flips a boolean like
  before, so mock-mode screens don't need a live backend to "log in". `currentUser` is now stored
  in context (not just a boolean) — set on login/signup response and re-hydrated on page load if a
  token is already in `localStorage`.
- **Commitments**: `src/data/real/commitmentsApi.ts` wraps `POST /problems/{id}/commitments`
  (used by `CommitModal`) and `POST /commitments/{id}/checkpoint` (not wired to any UI yet — no
  checkpoint/resolve-abandon-continue screen exists in the current mockup). Kept as a standalone
  module rather than added to `ProblemsPort`/`CurrentUserPort`, since neither port models a
  slot-spending write and widening both for one call site seemed worse than a small dedicated file.
- **Shared components**: `src/components/shared/` (TierChip, RoleChip, ClockRing, FocusSlotsWidget,
  PageHeader, Button, Modal) and `src/components/layout/` (AppShell, Sidebar). Every screen is
  CSS Modules, not inline styles.

### Design note: `currentUser` in context vs. re-fetching via the port

`AuthContext` now caches the `User` returned by login/signup (and re-fetches it once on page load
if a token is already stored), but `Sidebar` and `ProfilePage` were left calling
`currentUserPort.getCurrentUser()` directly on mount, same as before this pass, rather than being
switched to read `currentUser` from context. Reasoning: those two screens already had working
loading-state patterns (`useEffect` + local `useState`) that also fetch focus slots / commitment
history / committed problems in the same breath — splitting "user" onto context while leaving the
rest on the port would mean two different data-freshness stories for what's logically one
`GET /users/me` fetch. Keeping them on the port means one pattern, and `apiFetch`/browser HTTP
caching makes the extra round trip cheap. `AuthContext.currentUser` still exists and is populated
correctly — it's authoritative for "who just logged in" and available to any future screen that
wants to avoid the extra fetch (e.g. an app-shell header), it's just not wired into Sidebar/Profile
in this pass.

## Local development

```
npm install
npm run dev       # http://localhost:5173
npm run build     # type-check + production build
npm run lint       # oxlint
```

### Pointing at a live backend

By default the app runs entirely on mock/fixture data — no backend required. To exercise the real
HTTP ports against a running `services/backend-api` (e.g. port-forwarded from the local k8s
cluster):

```
cp .env.example .env.local
# edit .env.local if backend-api isn't on the default http://localhost:8000
npm run dev
```

`.env.local` is gitignored (via the `*.local` rule in `.gitignore`) — never commit real backend
URLs or secrets here beyond what's safe to share (this var isn't a secret, but keep the pattern
consistent).

Once live, verify manually:
- Sign up a new user (`/signup`) — should redirect to `/dashboard` on success; retrying the same
  email should surface the backend's 409 "email taken" message.
- Log in / log out — wrong password should show "Invalid email or password." without indicating
  which field was wrong.
- Discover a problem and commit a slot via `CommitModal` — on success the sidebar's focus-slots
  widget should update immediately (no page refresh). Try committing a 4th slot or re-committing
  to the same problem to see the server's `SLOT_LIMIT_EXCEEDED` / `ALREADY_COMMITTED` messages
  surfaced verbatim in the modal.
- Refresh the page while logged in — session should persist via the stored token until it expires
  or the backend returns a 401.

## Container

```
podman build -t avadhana/web:dev -f Containerfile .
podman run -d --rm -p 8082:8082 avadhana/web:dev
curl localhost:8082/healthz
```

Multi-stage build: `node:22-alpine` builds the static bundle, `nginx:1.27-alpine` serves it.
`nginx.conf` falls back all paths to `index.html` for client-side routing (react-router).

No Kubernetes manifest exists yet for this service (unlike `backend-api`/`ai-coordinator-worker`) —
add one under `infra/k8s/web/` when it's ready to run in-cluster.
