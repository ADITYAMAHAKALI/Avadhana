# Testing Strategy (Pre-Launch)

Living tracking doc for what needs to be tested before the SLC v1 pilot
ships, and who owns each item. This is a strategy/tracking doc, not a test
suite — no tests are written here. It restates CLAUDE.md's "Testing &
Verification Strategy" section (the authoritative source for *what* to
test) and assigns ownership given the current parallel-work split (this
agent: deployment/docs scaffolding only; two other engineers: backend API
domain logic and frontend wiring, in separate worktrees).

> **Note on sourcing:** this doc was scoped to restate a "Testing Checklist
> (pre-launch)" section expected in `TODO.md`. As of this writing, `TODO.md`
> does not contain a section by that name. This doc instead restates
> CLAUDE.md's "Testing & Verification Strategy" section, which covers the
> same ground in prose form. If a more detailed checklist gets added to
> `TODO.md` later, reconcile this doc against it.

## Ownership key

- **Backend** — the engineer building `services/backend-api/` domain logic
  (Core Commitment System `#3`, Problem Management `#10`, etc.). Unit/
  integration tests against the API and its data layer.
- **Frontend** — the engineer wiring `services/web/` to real endpoints.
  Component/interaction tests once mock-data ports are replaced with real
  API calls.
- **E2E (cross-cutting)** — needs the full deployed stack (frontend +
  backend + data tier) running together. Doesn't belong to either engineer
  alone; see "Where E2E tests should live" below.

Nothing in this doc is this agent's (deployment-scaffolding) responsibility
to write — this agent doesn't have the backend/frontend code the other two
are building. This doc tracks and assigns, it doesn't implement.

## Core constraint tests (CLAUDE.md "Testing & Verification Strategy")

| Test | Owner | Notes |
|---|---|---|
| Slot system: users cannot add a 4th problem while all 3 slots are full; error message is clear (not soft discouragement) | **Backend** | Depends on `FocusSlot` model + 3-slot enforcement (issue `#5`). |
| 90-day lock: commitment cannot be freed before day 90 | **Backend** | Depends on Commitment creation flow (`#6`) and the 90-day checkpoint job (`#7`). |
| 90-day checkpoint flow: resolve / abandon / continue prompts fire correctly at day 90 | **Backend** (job logic) + **Frontend** (UI flow) | Split responsibility — backend owns the job/state machine, frontend owns the prompt UI. Coordinate on the API contract between `#7` and whatever frontend issue consumes it. |
| Commitment-gated voice: non-committed readers cannot comment/vote; committed members can | **Backend** | Depends on commitment-gated authorization middleware (`#8`). |
| Abandoned status visibly shown on profile (reputational cost) | **Backend** (data) + **Frontend** (profile page, issue `#38`) | Backend must persist abandonment as a visible, non-reversible signal; frontend must actually render it — don't let this silently become backend-only. |
| Tier disputes: reclassification requires threshold agreement, lightweight to propose | **Backend** | Depends on Tier reclassification governance flow (`#14`) — unstarted. |

## AI Coordination tests (CLAUDE.md "AI Coordination Testing")

All items below depend on the AI Coordination Layer epic (`#18`), which is
currently unstarted (`SARVAM_USE_MOCK=true` everywhere, no real SARVAM
client). Listed here so they aren't forgotten, not because they're
actionable yet.

| Test | Owner | Notes |
|---|---|---|
| Off-topic detection accuracy (precision/recall on a test suite of on-topic/off-topic comments per problem type) | **Backend** (or a dedicated AI/ML-focused pass once `#18` lands) | Acceptable false-positive rate must be low — CLAUDE.md is explicit: "you can afford to upset committed members, not to suppress them." |
| Appeal flow: users can appeal blocks easily; appeals tracked for retraining | **Backend** | Depends on Appeal workflow (`#25`) and Moderation calibration feedback loop (`#26`). |
| Problem merging: conflict detection (same task in both, overlapping role assignments); committed members merged correctly (union); discussion history preserved | **Backend** | Depends on Problem merge mechanic + conflict detection (`#16`). Git-like conflict semantics per CLAUDE.md — human resolves conflicts, system only flags. |
| Checklist generation: spot-check accuracy/actionability against real problem discussions, not synthetic data | **Backend** | Depends on Markdown checklist generation (`#22`). Explicitly should be tested with real discussion data once available — synthetic test fixtures alone won't catch real drift. |
| Task assignment suggestions: consider current commitment load + past performance | **Backend** | Depends on task assignment suggestion logic, not yet scoped as its own issue — folds into the AI Coordination Layer epic generally. |

## End-to-end test (cross-cutting)

| Test | Owner | Notes |
|---|---|---|
| Sign up → commit to a problem → post as a committed member → hit the 90-day checkpoint | **E2E** — needs frontend + backend + deployed stack together, not ownable by either engineer alone | This is the one test in this list that cannot be satisfied by either engineer's unit/integration suite in isolation — it exercises auth, slot spending, commitment-gated posting, and the checkpoint job end-to-end against a real running stack. |

### Where E2E tests should eventually live

**Recommendation, not something to build now:** a `tests/e2e/` directory at
the repo root, using Playwright, running against the deployed
`docker-compose.prod.yml` stack (or an equivalent local Compose stack — the
same file works for both, see `docs/vps-deployment.md`). Reasoning:

- Playwright drives a real browser against the real frontend, which is the
  only way to exercise the full sign-up → commit → post → checkpoint path
  through actual UI interactions rather than mocked component state.
- Running against Compose (not the k8s dev cluster) keeps the E2E suite
  decoupled from Podman/kind-specific tooling — it only needs `docker
  compose up` and a URL to point Playwright at, so it can run in CI against
  an ephemeral Compose stack as well as manually against a real VPS pilot
  environment.
- `tests/e2e/` at the repo root (rather than nested under `services/web/` or
  `services/backend-api/`) reflects that this suite belongs to neither
  service alone — it's a whole-system test.

This is intentionally not scaffolded yet: it needs real backend endpoints
and real frontend wiring to exercise, neither of which exists yet (frontend
is still mock-data-backed per `TODO.md`; backend is still a skeleton).
Revisit once both land far enough to support a real sign-up → commit flow.

## Out of scope for this document

- Writing the actual tests (backend unit tests, frontend component tests,
  the E2E suite itself) — that's the responsibility of whoever owns each
  row above, once the underlying feature exists to test.
- CI wiring for running these tests automatically — today's CI
  (`.github/workflows/ci.yaml`) only builds container images and validates
  k8s manifests + (as of this doc) validates `docker-compose.prod.yml`
  syntax. Adding real test-execution jobs is a follow-up once test suites
  exist to run.
