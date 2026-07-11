# Avadhana — Build Checklist

Mirrors the GitHub issue backlog (`ADITYAMAHAKALI/Avadhana`) so progress can be tracked here or on GitHub. Check items off in either place — GitHub is the source of truth for status; this file is for a quick local read.

**2026-07-11 backlog hygiene pass**: 37 issues remain open (down from 59). Closed 22 issues that were already implemented and verified but still showing open on GitHub — epics `#3` (Core Commitment System) and `#62` (Solution Marketplace) are now fully done and closed; `#83` (Marketplace-vs-SLC-v1 sequencing) closed since the decision it tracked was made. Epics with real remaining scope stay open: `#10` `#18` `#28` `#35` `#55` `#60` `#87`. See each section below for exactly what's left.

**Local Kubernetes Dev Environment is done** — every service runs locally on Podman/kind via `make dev-up` (see `docs/local-dev.md`). **SLC v1 scope decided 2026-07-09**: ship a minimal-but-complete build of the core commitment mechanic — the thing that actually differentiates this platform — before investing in AI coordination or gamification polish. Items marked **(post-v1)** below are real backlog, not cut; they're sequenced after the initial deployed release validates the core mechanic with 5–10 real problems (spec Section 10). See "SLC v1 Release Plan" immediately below for the build order and reasoning.

## SLC v1 Release Plan

Goal: get a *simple, lovable, complete* version of the core loop — sign up → discover/create a problem → commit (spend a slot) → post/comment as a committed member → hit the 90-day checkpoint — actually deployed for a real pilot of 5–10 local problems, before building AI coordination or gamification. Not yet tracked as individual GitHub issues; file issues from this list if the plan is adopted.

Build order:

1. [x] User schema + auth ([#4](https://github.com/ADITYAMAHAKALI/Avadhana/issues/4))
2. [x] FocusSlot model + 3-slot enforcement ([#5](https://github.com/ADITYAMAHAKALI/Avadhana/issues/5))
3. [x] Commitment creation flow ([#6](https://github.com/ADITYAMAHAKALI/Avadhana/issues/6))
4. [x] Commitment-gated authorization middleware ([#8](https://github.com/ADITYAMAHAKALI/Avadhana/issues/8))
5. [x] 90-day checkpoint job + UI flow ([#7](https://github.com/ADITYAMAHAKALI/Avadhana/issues/7)) — `CheckpointModal` (resolve/abandon/continue) wired to a per-commitment "checkpoint due" affordance on the dashboard once `dayInCycle >= cycleLengthDays`
6. [x] CommitmentCheckpoint audit log ([#9](https://github.com/ADITYAMAHAKALI/Avadhana/issues/9))
7. [x] Problem schema + creation flow ([#11](https://github.com/ADITYAMAHAKALI/Avadhana/issues/11)) — `/problems/new` screen (tier picker surfaces the new Tier Classification Rubric), entry points from Sidebar and Discover
8. [x] Problem search & discovery ([#13](https://github.com/ADITYAMAHAKALI/Avadhana/issues/13)) — Discover page's search bar and filter chips are real, debounced, wired to `GET /problems` query params
9. [x] Feed core: post / comment / like ([#29](https://github.com/ADITYAMAHAKALI/Avadhana/issues/29)) — post composer, working like toggle, and lazily-loaded comment threads, all gated to committed members; also fixed two pre-existing bugs found along the way (gate notice rendering unconditionally, `lock` falling back to an arbitrary other commitment)
10. [x] Share, open/non-gated ([#30](https://github.com/ADITYAMAHAKALI/Avadhana/issues/30))
11. [x] Wire the web frontend off mock data onto the endpoints above (routes already scaffolded: Login, Signup, Dashboard, Discover, Problem, Profile) — real ports live behind `VITE_API_BASE_URL`, mock stays default for zero-setup `npm run dev`
12. [x] Reputation score computation ([#37](https://github.com/ADITYAMAHAKALI/Avadhana/issues/37)), tied to checkpoint events
13. [ ] Deploy to a single VPS via Docker Compose — see Deployment note below — `docker-compose.prod.yml` + `docs/vps-deployment.md` fully scaffolded and documented; **not yet actually deployed to a real VPS**. Not an engineering-scope gap (the runbook is ready), needs a real hosting account/domain — genuinely the next actionable step once you're ready to provision one.
14. [ ] Recruit the 5–10 real local problems the spec calls for (Section 10) and pilot — not started, not an engineering task, needs real-world outreach only a human can do

**Both remaining SLC v1 items are non-engineering blockers, not backlog gaps** — everything code-shaped in the original release plan is done.

**Deferred to post-v1** (revisit once the pilot validates the core mechanic and problem/discussion volume justifies the build cost):

- AI Coordination Layer (`#18`) in full — summarization, checklists, and off-topic detection are all more expensive to build than to do by hand at 5–10-problem scale
- Tier reclassification governance (`#14`), problem split (`#15`), problem merge (`#16`), ProblemRelationship audit log (`#17`) — the value shows up with problem volume the pilot won't have yet
- Polls (`#31`), task board (`#32`), asset uploads (`#33`), donation flow (`#34`) — self-contained features, safe to bolt on later without touching the core mechanic
- Badge schema + award rules (`#36`) — reputation score alone is enough signal for the pilot
- Appeal fraud throttling (`#58`) — nothing to throttle until AI moderation/appeals are live

**Deployment note:** reuse the Containerfiles already built for the local-dev epic (`#39`), but target a single VPS with Docker Compose — CLAUDE.md already names this as the eventual production target, and a managed k8s cluster is disproportionate cost/complexity for an unvalidated pilot.

## [Local Kubernetes Dev Environment (Podman)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/39) — done

- [x] [Install & configure Podman for local Kubernetes](https://github.com/ADITYAMAHAKALI/Avadhana/issues/40)
- [x] [Set up local k8s cluster + kubectl context](https://github.com/ADITYAMAHAKALI/Avadhana/issues/41)
- [x] [Containerize Backend API service](https://github.com/ADITYAMAHAKALI/Avadhana/issues/42)
- [x] [Containerize AI Coordinator Worker service](https://github.com/ADITYAMAHAKALI/Avadhana/issues/43)
- [x] [Containerize Moderation service](https://github.com/ADITYAMAHAKALI/Avadhana/issues/44)
- [x] [K8s manifests: PostgreSQL (local dev)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/45)
- [x] [K8s manifests: Redis (local dev)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/46)
- [x] [K8s manifests: Backend API](https://github.com/ADITYAMAHAKALI/Avadhana/issues/47)
- [x] [K8s manifests: AI Coordinator Worker](https://github.com/ADITYAMAHAKALI/Avadhana/issues/48)
- [x] [Local Ingress / routing](https://github.com/ADITYAMAHAKALI/Avadhana/issues/49)
- [x] [Local secrets management](https://github.com/ADITYAMAHAKALI/Avadhana/issues/50)
- [x] [Local SARVAM AI mock/stub](https://github.com/ADITYAMAHAKALI/Avadhana/issues/51)
- [x] [One-command dev bring-up (Makefile / script)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/52)
- [x] [CI: build & validate container images + manifests](https://github.com/ADITYAMAHAKALI/Avadhana/issues/53)
- [x] [Document local dev setup](https://github.com/ADITYAMAHAKALI/Avadhana/issues/54)

## [Core Commitment System](https://github.com/ADITYAMAHAKALI/Avadhana/issues/3) — done, epic closed 2026-07-11

User, focus slots, commitments, 90-day lock.

- [x] [Design User schema](https://github.com/ADITYAMAHAKALI/Avadhana/issues/4) — SQLAlchemy model + JWT auth (signup/login), bcrypt password hashing
- [x] [Implement FocusSlot model + 3-slot enforcement](https://github.com/ADITYAMAHAKALI/Avadhana/issues/5) — computed from active-commitment count (not a separate table); verified live: 4th commitment hard-blocked with 409 SLOT_LIMIT_EXCEEDED
- [x] [Implement Commitment creation flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/6) — `POST /problems/{id}/commitments`, wired end-to-end through CommitModal in the web frontend
- [x] [Implement 90-day checkpoint job + UI flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/7) — backend (`POST /commitments/{id}/checkpoint`: resolve/abandon/continue, lock enforced with no bypass, verified at day-89/90/91 boundaries) and frontend (`CheckpointModal`) both done; "job" stays computed-on-read rather than a scheduled sweep (no notification system exists to page a scheduled job into) — that's a deliberate scope call, not a gap
- [x] [Implement commitment-gated authorization middleware](https://github.com/ADITYAMAHAKALI/Avadhana/issues/8) — reusable `require_committed_member` FastAPI dependency; verified live: non-member POST blocked with 403 NOT_COMMITTED, committed member succeeds
- [x] [CommitmentCheckpoint audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/9) — insert-only, every transition logged, `GET /commitments/{id}/checkpoints`

## [Problem Management & Hierarchy](https://github.com/ADITYAMAHAKALI/Avadhana/issues/10)

Problems, tiers, search, split/merge.

- [x] [Problem schema + creation flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/11) — SLC v1 — backend (`POST /problems`, minimal schema, no hierarchy yet — `parentProblemTitle` hardcoded null) and frontend (`/problems/new`, entry points from Sidebar and Discover) both done and wired end-to-end
- [x] [Tier classification rubric (S–D)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/12) — SLC v1 — concrete hours/funding ranges per tier added to CLAUDE.md "Tier Classification Rubric", surfaced as helper text/tooltip in the problem-creation tier picker; addresses "Known Unknowns" #4
- [x] [Problem search & discovery](https://github.com/ADITYAMAHAKALI/Avadhana/issues/13) — SLC v1 — DiscoverPage's search bar and filter chips are real, debounced (250ms), wired to `GET /problems?q=&tier=&location=&category=` end-to-end
- [ ] [Tier reclassification governance flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/14) — post-v1
- [ ] [Problem split mechanic](https://github.com/ADITYAMAHAKALI/Avadhana/issues/15) — post-v1
- [ ] [Problem merge mechanic + conflict detection](https://github.com/ADITYAMAHAKALI/Avadhana/issues/16) — post-v1
- [ ] [ProblemRelationship audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/17) — post-v1
- [ ] [Problem-level resolution status: aggregate from checkpoints + objection window](https://github.com/ADITYAMAHAKALI/Avadhana/issues/100) — 2026-07-11, resolves CLAUDE.md Known Unknown #3 ("Problem Lifecycle Protocol")
- [ ] [Problem creation: surface similar existing problems before submit](https://github.com/ADITYAMAHAKALI/Avadhana/issues/102) — 2026-07-11, non-blocking duplicate nudge
- [ ] [Tier-informed recruitment target guidance on the problem page](https://github.com/ADITYAMAHAKALI/Avadhana/issues/103) — 2026-07-11, advisory only

## [AI Coordination Layer (SARVAM AI)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/18) — post-v1, entire epic deferred

Summarization, checklist generation, off-topic detection, moderation. Deferred until pilot problem/discussion volume makes manual summarization and moderation genuinely too slow — see SLC v1 Release Plan above for reasoning.

- [x] [SARVAM AI client integration](https://github.com/ADITYAMAHAKALI/Avadhana/issues/19) — built before the SLC v1 re-scope landed; real client + mock deploy manifest done, no real jobs consume it yet
- [ ] [AI agent invocation trigger](https://github.com/ADITYAMAHAKALI/Avadhana/issues/20)
- [ ] [Summarization generation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/21)
- [ ] [Markdown checklist generation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/22)
- [ ] [Off-topic detection + confidence scoring](https://github.com/ADITYAMAHAKALI/Avadhana/issues/23)
- [ ] [Auto-block + human review queue](https://github.com/ADITYAMAHAKALI/Avadhana/issues/24)
- [ ] [Appeal workflow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/25)
- [ ] [Moderation calibration feedback loop](https://github.com/ADITYAMAHAKALI/Avadhana/issues/26)
- [ ] [AIInvocation audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/27)

## [Problem-Specific Feed & Interactions](https://github.com/ADITYAMAHAKALI/Avadhana/issues/28)

- [x] [Feed core: post / comment / like](https://github.com/ADITYAMAHAKALI/Avadhana/issues/29) — SLC v1 — post composer, working like toggle, and lazily-loaded comment threads, all gated to committed members and verified live end-to-end
- [x] [Share (open, non-gated)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/30) — SLC v1 — no dedicated endpoint needed; all problem/feed GETs are public/unauthenticated by design, verified live
- [ ] [Polls](https://github.com/ADITYAMAHAKALI/Avadhana/issues/31) — post-v1
- [ ] [Task board: create / pick up / handover tasks](https://github.com/ADITYAMAHAKALI/Avadhana/issues/32) — post-v1
- [ ] [Asset uploads](https://github.com/ADITYAMAHAKALI/Avadhana/issues/33) — post-v1
- [ ] [Donation flow (Backer)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/34) — post-v1 — ⚠️ open design question: slot-gated or open to non-committed supporters? Decide before building.
- [ ] [Problem feed: threaded/nested replies + a real sort](https://github.com/ADITYAMAHAKALI/Avadhana/issues/98) — 2026-07-11, "Reddit-like feed" request; needs `Comment.parent_comment_id`, backend + frontend both, no vote mechanic (deliberately, see issue body)

## [Gamification & Reputation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/35)

Rewards follow-through, not activity — do not build a second engagement-farming loop.

- [ ] [Badge schema + award rules](https://github.com/ADITYAMAHAKALI/Avadhana/issues/36) — post-v1
- [ ] [Tier-weighted reputation deltas](https://github.com/ADITYAMAHAKALI/Avadhana/issues/101) — 2026-07-11, replaces flat +20/-15/0 with a tier-scaled table per CLAUDE.md's "Problem Lifecycle Protocol"
- [x] [Reputation score computation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/37) — SLC v1 — flat deltas on checkpoint events only (resolve +20, abandon -15, continue +0), verified never moves on posts/likes; tier-weighting deferred (post-v1, needs badges work too)
- [x] [Profile page](https://github.com/ADITYAMAHAKALI/Avadhana/issues/38) — SLC v1 — wired to real data via `CurrentUserPort` (committed problems, commitment history, reputation)

## [Security & Moderation Safety](https://github.com/ADITYAMAHAKALI/Avadhana/issues/55)

- [x] [API key & secrets management policy](https://github.com/ADITYAMAHAKALI/Avadhana/issues/56) — SLC v1 — `docs/security-policy.md`
- [x] [Immutable audit logging for moderation actions](https://github.com/ADITYAMAHAKALI/Avadhana/issues/57) — SLC v1 — established as the pattern via `CommitmentCheckpoint` (insert-only, never updated/deleted); no moderation actions exist yet to log (AI moderation is post-v1), so this is the principle + a working example, not moderation-specific logging itself
- [ ] [Appeal fraud throttling](https://github.com/ADITYAMAHAKALI/Avadhana/issues/58) — post-v1 (no appeals to throttle until AI moderation is live)
- [x] [Human override for moderators](https://github.com/ADITYAMAHAKALI/Avadhana/issues/59) — SLC v1 — `is_platform_admin` on User (no self-service API path to set it, deliberate — manual DB update only), admin-only hide/restore endpoints for posts and comments, immutable `ModerationOverrideEvent` audit log, per-problem moderation-log endpoint (admin-only for this baseline pass; widening to committed members is a natural follow-up); verified live end-to-end

## [Web Frontend (React)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/60)

`services/web/` — React + TS + Vite, ported from the Claude Design mockup. Mock data layer behind ports until backend domain endpoints exist (issues #4-17).

- [x] [Implement Avadhana Web app shell from Claude Design mockup](https://github.com/ADITYAMAHAKALI/Avadhana/issues/61)
- [x] Sidebar dead-link fix + Commit/Checkpoint modal accessibility ([#74](https://github.com/ADITYAMAHAKALI/Avadhana/issues/74), [#75](https://github.com/ADITYAMAHAKALI/Avadhana/issues/75)) — removed the hardcoded fixture-problem-id nav links, real per-problem Graph/Coordinator navigation added; modal cards are real `<button>`s or `role="button"`+keyboard-handled, dialog semantics + focus management added, verified interactively
- [ ] [Web frontend is not mobile-responsive — no `@media` queries anywhere](https://github.com/ADITYAMAHAKALI/Avadhana/issues/86) — confirmed zero `@media` rules across all 22 CSS modules despite a viewport meta tag existing; `AppShell`/`Sidebar` collapsing to a mobile nav is the highest-leverage single fix since every page inherits it
- [ ] [Share button on ProblemPage has no handler](https://github.com/ADITYAMAHAKALI/Avadhana/issues/96) — 2026-07-11, real regression against the intent of closed #30 (backend read-side is public, but the UI button itself is a no-op)
- [ ] [ProblemPage has multiple decorative/non-functional controls](https://github.com/ADITYAMAHAKALI/Avadhana/issues/97) — 2026-07-11, tabs that don't switch, dead breadcrumb, hardcoded avatar stack, fake-live AI summary card
- [ ] [Polish the non-committed visitor "browse + share, don't engage" experience](https://github.com/ADITYAMAHAKALI/Avadhana/issues/99) — 2026-07-11, depends on #96

## [Solution Marketplace](https://github.com/ADITYAMAHAKALI/Avadhana/issues/62) — done, epic closed 2026-07-11

B2B/B2G RFP-to-Solution matching marketplace (multi-attribute + multi-embedding Reciprocal Rank Fusion). **Independent of the civic 3-slot/90-day-lock/commitment-gated-voice mechanic** — see CLAUDE.md "Solution Marketplace Architecture" for the full design, domain model, and open questions, and `architecture/modules/05-solution-marketplace.drawio.png` / `06-marketplace-matching-flow.drawio.png` for diagrams. **2026-07-10: explicit reprioritization call made** (previously an open product decision, tracked by #83 — now closed) — Marketplace was built out fully, ahead of the SLC v1 pilot (VPS deploy + real problem recruitment are still the two open SLC v1 items). All 11 sub-issues closed. Remaining real gaps: legal/ToS review before real B2B usage ([#78](https://github.com/ADITYAMAHAKALI/Avadhana/issues/78), scaffolding only so far), supply-side cold-start plan ([#82](https://github.com/ADITYAMAHAKALI/Avadhana/issues/82)), IDOR fix already shipped ([#84](https://github.com/ADITYAMAHAKALI/Avadhana/issues/84), closed).

- [x] [Design Organization + membership schema](https://github.com/ADITYAMAHAKALI/Avadhana/issues/63)
- [x] [RFP schema + posting flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/64)
- [x] [Solution schema + publishing flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/65)
- [x] [Structured attribute-match scoring (no ML)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/66)
- [x] [Embeddings provider integration](https://github.com/ADITYAMAHAKALI/Avadhana/issues/67) — OpenAI `text-embedding-3-small`, pgvector on Postgres with a SQLite-portable fallback type for tests
- [x] [Matching engine: rank fusion (RRF)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/68) — async job on ai-coordinator-worker's `marketplace-matching` queue
- [x] [Matching results UI: ranked shortlist + explainability](https://github.com/ADITYAMAHAKALI/Avadhana/issues/69) — trigger + poll flow, full per-signal score/rank breakdown, verified live in browser
- [x] [Community-promotion bridge (RFP → civic Problem)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/70) — caller supplies tier explicitly (no RFP-side rubric equivalent to infer it from)
- [x] [Free-quota tracking + billing paywall gate](https://github.com/ADITYAMAHAKALI/Avadhana/issues/71) — quota tracked + `BillingEvent` ledger; no payment processor wired (out of scope per CLAUDE.md)
- [x] [Web frontend: Marketplace tab](https://github.com/ADITYAMAHAKALI/Avadhana/issues/72)
- [x] [Free-tier abuse safeguards](https://github.com/ADITYAMAHAKALI/Avadhana/issues/73) — partial: per-user rate limit on Organization creation; doesn't stop multi-account abuse (documented gap)

## [Mobile App (Expo / React Native)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/87) — in progress

`apps/mobile/` (new top-level directory, own `package.json`, doesn't touch `services/web/`). Expo managed workflow + Expo Router. Talks to the same `services/backend-api` REST/JWT contract web uses (`services/web/src/data/real/httpClient.ts`) — no backend changes needed for the base client, and CLAUDE.md's core constraints (3-slot, 90-day lock, commitment-gated voice) are inherited for free since they're enforced server-side. JWT stored via `expo-secure-store` (iOS Keychain / Android Keystore) from day one — deliberately not repeating web's `localStorage` JWT storage, flagged as a latent XSS-exfiltration risk in the 2026-07-10 security audit (`audits/security-audit-2026-07-10.md`). **2026-07-11: explicit reprioritization call made** (per issue #87's own sequencing note and the #83 precedent) — mobile epic starts now, in parallel with the two still-open SLC v1 items (VPS deploy, real problem recruitment) and the in-flight Marketplace work; neither civic-core-loop item is being deprioritized by this.

- [x] [Expo app scaffold + navigation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/88) — Expo Router, `(tabs)` group (dashboard/discover/profile) + `problems/[problemId]` stack screen; template demo screens/assets removed
- [x] [Auth flow (signup/login) with expo-secure-store](https://github.com/ADITYAMAHAKALI/Avadhana/issues/89) — token persisted via `expo-secure-store`; request/response shapes verified against the real `backend-api` app object (sqlite-backed, same technique as `tests/integration/conftest.py`): signup → token → authenticated `GET /users/me` → login → 401-on-bad-password, all matching the mobile client's expected contract
- [ ] [Commit modal: role pick + 90-day-lock acknowledgment](https://github.com/ADITYAMAHAKALI/Avadhana/issues/90)
- [ ] [Checkpoint flow (resolve/continue/abandon)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/91)
- [ ] [Problem feed: read + commitment-gated post/comment/like](https://github.com/ADITYAMAHAKALI/Avadhana/issues/92)
- [ ] [Push notifications for checkpoint-due reminders](https://github.com/ADITYAMAHAKALI/Avadhana/issues/93) — addresses CLAUDE.md's Critical Open Issue #2 (hard-lock frustration); needs a backend-side scheduled trigger, not just a mobile client change
- [ ] [Decide Marketplace scope for v1 mobile](https://github.com/ADITYAMAHAKALI/Avadhana/issues/94)
- [ ] [Build/distribution: EAS vs internal-only first pass](https://github.com/ADITYAMAHAKALI/Avadhana/issues/95)

## Audit Findings (2026-07-10/11) — remaining open items

Filed by the four `audits/*.md` reports and not mapped to any epic above. Fixed items (#74-77, #84, #85) are already reflected in their relevant sections above and in closed GitHub issues — this section is only what's still open.

- [ ] [Legal review + ToS/liability disclaimer before Actor role and Marketplace RFP flow reach real users](https://github.com/ADITYAMAHAKALI/Avadhana/issues/78) — **critical, needs your action, not engineering**: scaffolding shipped (`docs/legal-draft-DO-NOT-USE-WITHOUT-REVIEW.md`, visible warning UI in `CommitModal`/`NewRFPPage`), but a real lawyer reviewing actual jurisdiction-specific exposure is still outstanding. CLAUDE.md Critical Open Issue #4.
- [ ] [Add HPA manifest for ai-coordinator-worker](https://github.com/ADITYAMAHAKALI/Avadhana/issues/79) — low priority pre-launch, no autoscaling story exists yet for any service (all `replicas: 1`)
- [ ] [Add read-cache strategy for problem feed and marketplace browsing](https://github.com/ADITYAMAHAKALI/Avadhana/issues/80) — low priority pre-launch, no caching layer exists (Redis is only used as the RQ broker today)
- [ ] [Track GTM/pilot seeding plan as real issues](https://github.com/ADITYAMAHAKALI/Avadhana/issues/81) — landing page copy drafted (`docs/landing-page-copy-draft.md`, not yet wired to a live route); recruiting the 5-10 real pilot problems and the launch blog post remain outreach-only work, same blocker as SLC v1 item 14 above
- [ ] [Solution Marketplace: no supply-side (Solution listing) cold-start plan](https://github.com/ADITYAMAHAKALI/Avadhana/issues/82) — product decision (which vertical/geography to seed first, direct outreach vs. platform-authored listings), not a build task

## Security Checklist (pre-launch)

Not yet tracked as individual GitHub issues — derived from CLAUDE.md's Security & Solo-Dev Architecture section plus standard web-app hardening. File issues under epic `#55` if adopted.

- [x] Secrets never committed; `.env` + `.gitignore` locally, k8s Secrets in the local cluster, a real secrets manager before VPS prod
- [x] Password hashing with bcrypt/argon2 — never plaintext, never reversible encryption — bcrypt via passlib
- [ ] Session/JWT tokens signed, short-lived, and rotated on privilege change (e.g. new commitment created) — signed (HS256) and expire after 7 days; no rotation-on-privilege-change yet
- [x] Rate limiting on auth endpoints (login, signup, password reset) to prevent brute force — 5/minute (slowapi, in-memory), verified live (4 requests through, 5th+ gets 429)
- [x] Rate limiting on the API generally, especially anything that can trigger a downstream SARVAM call — 60/minute general default
- [x] SQL injection protection — parameterized queries / ORM only, no raw string interpolation — SQLAlchemy ORM throughout, no raw SQL anywhere in the codebase
- [x] CORS configured to allow only the deployed web frontend origin — `CORS_ALLOWED_ORIGIN` env var, fails safe to the Vite dev origin (never `*`) when unset, verified live
- [ ] TLS/HTTPS terminated at ingress (local) and at the VPS reverse proxy (deployed) — optional Caddy service scaffolded in `docker-compose.prod.yml` but not enabled by default (no real domain yet)
- [ ] CSRF protection if any cookie-based session auth is used — N/A as things stand: auth is JWT bearer only, no cookie-based session exists; revisit if that changes
- [ ] Dependency vulnerability scanning (Dependabot / `pip-audit` / `npm audit`) wired into CI
- [ ] API key rotation policy documented and followed for SARVAM keys — cadence documented in `docs/security-policy.md`; "followed" isn't something a checklist item can verify, needs an actual rotation to happen
- [ ] AI API calls logged for cost/audit without logging full user-data payloads (per CLAUDE.md) — no AI calls happen yet in the SLC v1 path (AI coordination is post-v1)
- [x] All moderation actions (auto-block, appeal, appeal outcome) immutable — insert-only, never update/delete — `ModerationOverrideEvent` follows this exactly; no auto-block/appeal exists yet (post-v1), so this covers the human-override path only so far
- [x] Human override path for moderators exists and is exercised at least once before public launch — admin hide/restore for posts and comments, verified live end-to-end (hide excludes from feed, audit log records it, restore brings it back)

## Testing Checklist (pre-launch)

Not yet tracked as individual GitHub issues — derived from CLAUDE.md's Testing & Verification Strategy. File issues under the relevant epic if adopted.

- [x] Slot system: a 4th commitment attempt is blocked with a clear error, not soft discouragement — automated test + verified live (409 `SLOT_LIMIT_EXCEEDED`)
- [x] 90-day lock: a commitment cannot be freed before day 90; no code path bypasses it — automated tests at day-89/90/91 boundaries
- [ ] 90-day checkpoint flow: resolve / abandon / continue all tested, including edge cases (exactly day 90, timezone handling) — resolve/abandon/continue are automated-tested on the backend (UTC); frontend timezone-display edge cases (DST, non-UTC users) haven't been specifically tested
- [x] Commitment-gated voice: non-committed readers can read/share but cannot comment/vote; committed members can — automated tests + verified live (401/403/200 matrix)
- [x] Abandoned status is visible on the abandoning user's profile and is not reversible after the fact — surfaced via commitment-history on the Profile page; no endpoint exists to reverse a checkpoint decision
- [ ] Tier reclassification requires threshold agreement and stays lightweight to propose (once built, post-v1)
- [ ] Problem merge: conflict detection (same task in both, conflicting role assignments) and human resolution flow (once built, post-v1)
- [ ] Off-topic detection precision/recall measured against a labeled test set per problem type; false-positive rate is the metric to protect (once built, post-v1)
- [ ] Appeal flow tracked end-to-end and feeds calibration data (once built, post-v1)
- [x] CI runs unit + integration tests on every PR; container images and k8s manifests validate — `test-backend-api` and `test-ai-coordinator-worker` jobs added alongside `build-images`/`validate-manifests`/`validate-compose`
- [ ] End-to-end test of the full SLC v1 loop: sign up → commit → post as committed member → hit checkpoint — exercised manually (curl/Node scripts) during this session's verification passes, but no automated E2E suite (e.g. Playwright against the deployed stack, per `docs/testing-strategy.md`'s recommendation) exists yet

## Marketing & Launch

Tracked as GitHub issue [#81](https://github.com/ADITYAMAHAKALI/Avadhana/issues/81) (see "Audit Findings" above) — kept here too as the detailed checklist. The spec (Section 9, risk 5 — "Growth tension") is explicit that the friction is the pitch, not a bug to hide — messaging should lead with it, not apologize for it.

- [x] Landing page copy that explains *why* the constraints exist (3 slots, 90-day lock, commitment-gated voice) before asking anyone to sign up — drafted (`docs/landing-page-copy-draft.md`), not yet wired to a live route
- [ ] Launch blog post on the core thesis — "commitment over engagement" — aimed at people frustrated with performative online activism (the Change.org comparison from spec Section 3.1)
- [ ] Seed the pilot: identify and directly recruit the 5–10 real local problems plus initial Thinkers/Actors/Backers per problem — cold start (spec Section 9, risk 1) doesn't solve itself and needs manual outreach before public launch
- [ ] Follow-up blog series once the pilot has real data — e.g. "what happened when we forced 10 people to pick 3 problems," case studies from resolved problems
- [ ] Public, shareable problem pages (via the existing Share mechanic) double as organic content/SEO — the product itself produces shareable progress without a separate content team
- [ ] Public metrics page reporting the Section 8 success metrics (% resolved by day 90, committed-to-observer ratio, role distribution) — proof points for later marketing, consistent with the platform's own accountability-first ethos
- [ ] Consider a Show HN / Product Hunt style launch only after the pilot has at least one resolved or meaningfully progressed problem to point to — leading with an empty platform undercuts the "outcomes over spectating" pitch
- [ ] Legal review of Actor-role language (RTI filings, legal action) before any of this messaging goes public, per spec Section 9 risk 4 — marketing copy shouldn't imply legal backing the platform doesn't provide; tracked as [#78](https://github.com/ADITYAMAHAKALI/Avadhana/issues/78), same underlying gap
