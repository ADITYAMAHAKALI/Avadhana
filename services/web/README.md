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
  `ModerationPort`); `src/data/mock/` has the only implementations today, seeded with fixture data
  matching the design mockup's example content. `src/data/index.ts` is the composition root —
  swap in real HTTP-backed implementations there once `services/backend-api` grows domain
  endpoints (issues #4-17); no screen component needs to change.
- **Auth**: `src/context/AuthContext.tsx` is a mock (`login()` just flips a boolean) — real
  credential verification is a later backend concern.
- **Shared components**: `src/components/shared/` (TierChip, RoleChip, ClockRing, FocusSlotsWidget,
  PageHeader, Button, Modal) and `src/components/layout/` (AppShell, Sidebar). Every screen is
  CSS Modules, not inline styles.

## Local development

```
npm install
npm run dev       # http://localhost:5173
npm run build     # type-check + production build
```

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
