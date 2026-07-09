# Avadhana — Build Checklist

Mirrors the GitHub issue backlog (`ADITYAMAHAKALI/Avadhana`, epics `#3` `#10` `#18` `#28` `#35` `#39` `#55` `#60`) so progress can be tracked here or on GitHub. Check items off in either place — GitHub is the source of truth for status; this file is for a quick local read.

**Local Kubernetes Dev Environment is done** — every service runs locally on Podman/kind via `make dev-up` (see `docs/local-dev.md`). **SLC v1 scope decided 2026-07-09**: ship a minimal-but-complete build of the core commitment mechanic — the thing that actually differentiates this platform — before investing in AI coordination or gamification polish. Items marked **(post-v1)** below are real backlog, not cut; they're sequenced after the initial deployed release validates the core mechanic with 5–10 real problems (spec Section 10). See "SLC v1 Release Plan" immediately below for the build order and reasoning.

## SLC v1 Release Plan

Goal: get a *simple, lovable, complete* version of the core loop — sign up → discover/create a problem → commit (spend a slot) → post/comment as a committed member → hit the 90-day checkpoint — actually deployed for a real pilot of 5–10 local problems, before building AI coordination or gamification. Not yet tracked as individual GitHub issues; file issues from this list if the plan is adopted.

Build order:

1. [ ] User schema + auth ([#4](https://github.com/ADITYAMAHAKALI/Avadhana/issues/4))
2. [ ] FocusSlot model + 3-slot enforcement ([#5](https://github.com/ADITYAMAHAKALI/Avadhana/issues/5))
3. [ ] Commitment creation flow ([#6](https://github.com/ADITYAMAHAKALI/Avadhana/issues/6))
4. [ ] Commitment-gated authorization middleware ([#8](https://github.com/ADITYAMAHAKALI/Avadhana/issues/8))
5. [ ] 90-day checkpoint job + UI flow ([#7](https://github.com/ADITYAMAHAKALI/Avadhana/issues/7))
6. [ ] CommitmentCheckpoint audit log ([#9](https://github.com/ADITYAMAHAKALI/Avadhana/issues/9))
7. [ ] Problem schema + creation flow ([#11](https://github.com/ADITYAMAHAKALI/Avadhana/issues/11)) — tier set once at creation, no reclassification yet
8. [ ] Problem search & discovery ([#13](https://github.com/ADITYAMAHAKALI/Avadhana/issues/13))
9. [ ] Feed core: post / comment / like ([#29](https://github.com/ADITYAMAHAKALI/Avadhana/issues/29))
10. [ ] Share, open/non-gated ([#30](https://github.com/ADITYAMAHAKALI/Avadhana/issues/30))
11. [ ] Wire the web frontend off mock data onto the endpoints above (routes already scaffolded: Login, Signup, Dashboard, Discover, Problem, Profile)
12. [ ] Reputation score computation ([#37](https://github.com/ADITYAMAHAKALI/Avadhana/issues/37)), tied to checkpoint events
13. [ ] Deploy to a single VPS via Docker Compose — see Deployment note below
14. [ ] Recruit the 5–10 real local problems the spec calls for (Section 10) and pilot

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

## [Core Commitment System](https://github.com/ADITYAMAHAKALI/Avadhana/issues/3) — SLC v1 priority

User, focus slots, commitments, 90-day lock.

- [ ] [Design User schema](https://github.com/ADITYAMAHAKALI/Avadhana/issues/4)
- [ ] [Implement FocusSlot model + 3-slot enforcement](https://github.com/ADITYAMAHAKALI/Avadhana/issues/5)
- [ ] [Implement Commitment creation flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/6)
- [ ] [Implement 90-day checkpoint job + UI flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/7)
- [ ] [Implement commitment-gated authorization middleware](https://github.com/ADITYAMAHAKALI/Avadhana/issues/8)
- [ ] [CommitmentCheckpoint audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/9)

## [Problem Management & Hierarchy](https://github.com/ADITYAMAHAKALI/Avadhana/issues/10)

Problems, tiers, search, split/merge.

- [ ] [Problem schema + creation flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/11) — SLC v1
- [ ] [Tier classification rubric (S–D)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/12) — SLC v1 (needed to set tier at creation)
- [ ] [Problem search & discovery](https://github.com/ADITYAMAHAKALI/Avadhana/issues/13) — SLC v1
- [ ] [Tier reclassification governance flow](https://github.com/ADITYAMAHAKALI/Avadhana/issues/14) — post-v1
- [ ] [Problem split mechanic](https://github.com/ADITYAMAHAKALI/Avadhana/issues/15) — post-v1
- [ ] [Problem merge mechanic + conflict detection](https://github.com/ADITYAMAHAKALI/Avadhana/issues/16) — post-v1
- [ ] [ProblemRelationship audit log](https://github.com/ADITYAMAHAKALI/Avadhana/issues/17) — post-v1

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

- [ ] [Feed core: post / comment / like](https://github.com/ADITYAMAHAKALI/Avadhana/issues/29) — SLC v1
- [ ] [Share (open, non-gated)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/30) — SLC v1
- [ ] [Polls](https://github.com/ADITYAMAHAKALI/Avadhana/issues/31) — post-v1
- [ ] [Task board: create / pick up / handover tasks](https://github.com/ADITYAMAHAKALI/Avadhana/issues/32) — post-v1
- [ ] [Asset uploads](https://github.com/ADITYAMAHAKALI/Avadhana/issues/33) — post-v1
- [ ] [Donation flow (Backer)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/34) — post-v1 — ⚠️ open design question: slot-gated or open to non-committed supporters? Decide before building.

## [Gamification & Reputation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/35)

Rewards follow-through, not activity — do not build a second engagement-farming loop.

- [ ] [Badge schema + award rules](https://github.com/ADITYAMAHAKALI/Avadhana/issues/36) — post-v1
- [ ] [Reputation score computation](https://github.com/ADITYAMAHAKALI/Avadhana/issues/37) — SLC v1 (movement on resolve/abandon events only)
- [ ] [Profile page](https://github.com/ADITYAMAHAKALI/Avadhana/issues/38) — SLC v1 (already scaffolded in web frontend against mock data)

## [Security & Moderation Safety](https://github.com/ADITYAMAHAKALI/Avadhana/issues/55)

- [ ] [API key & secrets management policy](https://github.com/ADITYAMAHAKALI/Avadhana/issues/56) — SLC v1
- [ ] [Immutable audit logging for moderation actions](https://github.com/ADITYAMAHAKALI/Avadhana/issues/57) — SLC v1
- [ ] [Appeal fraud throttling](https://github.com/ADITYAMAHAKALI/Avadhana/issues/58) — post-v1 (no appeals to throttle until AI moderation is live)
- [ ] [Human override for moderators](https://github.com/ADITYAMAHAKALI/Avadhana/issues/59) — SLC v1 (baseline override capability, ahead of full AI moderation)

## [Web Frontend (React)](https://github.com/ADITYAMAHAKALI/Avadhana/issues/60)

`services/web/` — React + TS + Vite, ported from the Claude Design mockup. Mock data layer behind ports until backend domain endpoints exist (issues #4-17).

- [x] [Implement Avadhana Web app shell from Claude Design mockup](https://github.com/ADITYAMAHAKALI/Avadhana/issues/61)

## Security Checklist (pre-launch)

Not yet tracked as individual GitHub issues — derived from CLAUDE.md's Security & Solo-Dev Architecture section plus standard web-app hardening. File issues under epic `#55` if adopted.

- [ ] Secrets never committed; `.env` + `.gitignore` locally, k8s Secrets in the local cluster, a real secrets manager before VPS prod
- [ ] Password hashing with bcrypt/argon2 — never plaintext, never reversible encryption
- [ ] Session/JWT tokens signed, short-lived, and rotated on privilege change (e.g. new commitment created)
- [ ] Rate limiting on auth endpoints (login, signup, password reset) to prevent brute force
- [ ] Rate limiting on the API generally, especially anything that can trigger a downstream SARVAM call
- [ ] SQL injection protection — parameterized queries / ORM only, no raw string interpolation
- [ ] CORS configured to allow only the deployed web frontend origin
- [ ] TLS/HTTPS terminated at ingress (local) and at the VPS reverse proxy (deployed)
- [ ] CSRF protection if any cookie-based session auth is used
- [ ] Dependency vulnerability scanning (Dependabot / `pip-audit` / `npm audit`) wired into CI
- [ ] API key rotation policy documented and followed for SARVAM keys
- [ ] AI API calls logged for cost/audit without logging full user-data payloads (per CLAUDE.md)
- [ ] All moderation actions (auto-block, appeal, appeal outcome) immutable — insert-only, never update/delete
- [ ] Human override path for moderators exists and is exercised at least once before public launch

## Testing Checklist (pre-launch)

Not yet tracked as individual GitHub issues — derived from CLAUDE.md's Testing & Verification Strategy. File issues under the relevant epic if adopted.

- [ ] Slot system: a 4th commitment attempt is blocked with a clear error, not soft discouragement
- [ ] 90-day lock: a commitment cannot be freed before day 90; no code path bypasses it
- [ ] 90-day checkpoint flow: resolve / abandon / continue all tested, including edge cases (exactly day 90, timezone handling)
- [ ] Commitment-gated voice: non-committed readers can read/share but cannot comment/vote; committed members can
- [ ] Abandoned status is visible on the abandoning user's profile and is not reversible after the fact
- [ ] Tier reclassification requires threshold agreement and stays lightweight to propose (once built, post-v1)
- [ ] Problem merge: conflict detection (same task in both, conflicting role assignments) and human resolution flow (once built, post-v1)
- [ ] Off-topic detection precision/recall measured against a labeled test set per problem type; false-positive rate is the metric to protect (once built, post-v1)
- [ ] Appeal flow tracked end-to-end and feeds calibration data (once built, post-v1)
- [ ] CI runs unit + integration tests on every PR; container images and k8s manifests validate (already true per `#53` — keep enforcing as services gain real logic)
- [ ] End-to-end test of the full SLC v1 loop: sign up → commit → post as committed member → hit checkpoint

## Marketing & Launch

Not yet tracked as individual GitHub issues. The spec (Section 9, risk 5 — "Growth tension") is explicit that the friction is the pitch, not a bug to hide — messaging should lead with it, not apologize for it.

- [ ] Landing page copy that explains *why* the constraints exist (3 slots, 90-day lock, commitment-gated voice) before asking anyone to sign up — the friction has to be sold, not discovered after the fact
- [ ] Launch blog post on the core thesis — "commitment over engagement" — aimed at people frustrated with performative online activism (the Change.org comparison from spec Section 3.1)
- [ ] Seed the pilot: identify and directly recruit the 5–10 real local problems plus initial Thinkers/Actors/Backers per problem — cold start (spec Section 9, risk 1) doesn't solve itself and needs manual outreach before public launch
- [ ] Follow-up blog series once the pilot has real data — e.g. "what happened when we forced 10 people to pick 3 problems," case studies from resolved problems
- [ ] Public, shareable problem pages (via the existing Share mechanic) double as organic content/SEO — the product itself produces shareable progress without a separate content team
- [ ] Public metrics page reporting the Section 8 success metrics (% resolved by day 90, committed-to-observer ratio, role distribution) — proof points for later marketing, consistent with the platform's own accountability-first ethos
- [ ] Consider a Show HN / Product Hunt style launch only after the pilot has at least one resolved or meaningfully progressed problem to point to — leading with an empty platform undercuts the "outcomes over spectating" pitch
- [ ] Legal review of Actor-role language (RTI filings, legal action) before any of this messaging goes public, per spec Section 9 risk 4 — marketing copy shouldn't imply legal backing the platform doesn't provide
