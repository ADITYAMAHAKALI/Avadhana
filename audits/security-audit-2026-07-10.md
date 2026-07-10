# Security Audit — 2026-07-10

Scope: `services/backend-api`, `services/ai-coordinator-worker`, `services/moderation`,
`services/web`, `services/sarvam-mock`, `infra/k8s`, `docker-compose.prod.yml`,
`.env.example`, `docs/security-policy.md`. Code-verified (read actual source), not a
docs-only review. Compared against the intended security model documented in
`CLAUDE.md` ("Security & Solo-Dev Architecture", "AI Coordination Architecture",
"Solution Marketplace Architecture").

This is an early-stage repo (see `TODO.md`) — a lot of CLAUDE.md's aspirational AI
moderation/appeal machinery genuinely does not exist yet. That is reported here as
"not yet implemented," which is expected and already tracked by existing issues
(#18–27, #55–59), not treated as a novel finding. The findings that matter are: (a)
things that exist but are built insecurely, and (b) `docs/security-policy.md` itself
being stale relative to what has since merged.

## Current Status

**1. Secrets/API key handling.** Solid. `.gitignore` excludes `.env`/`.env.*`,
allow-lists `.env.example` (verified: only `.env.example` and
`services/web/.env.example` are tracked, both placeholder-only — no real secret
values in either). `infra/k8s/scripts/create-secrets.sh` sources local `.env` into two
k8s Secrets (`avadhana-postgres-secret`, `avadhana-app-secret`) and never echoes
values to stdout. No hardcoded SARVAM/DB/JWT secrets found anywhere in committed
source (`grep -rn "SARVAM\|api_key\|SECRET\|PASSWORD"` across services/infra turned up
only doc references, env-var plumbing, and password *field names*, never literal
secret values). `services/backend-api/app/core/security.py` builds the JWT from
`settings.jwt_secret`, itself sourced from `JWT_SECRET` env var. No embeddings/API
keys baked into any Containerfile.

**2. AuthN/AuthZ — commitment-gated voice.** Implemented and enforced server-side,
not just in the UI. `app/core/auth_dependencies.py::get_current_user` resolves the
caller from a Bearer JWT (401 on missing/invalid/expired token). `app/services/
commitment_gate.py::require_committed_member` is a FastAPI dependency that queries an
**active** `Commitment` row for `(user_id, problem_id)` and 403s
(`NOT_COMMITTED`) if none exists. `app/routers/feed.py` wires this dependency onto
`create_post_route`, `like_post_route`, and `create_comment_route` (lines 30-34,
66-70, 89-94) — a non-committed user hitting these endpoints directly (bypassing the
UI) gets a 403, confirmed by reading the dependency chain, not just the route
signature. `require_platform_admin` (same file) gates the moderation-override
endpoints and cannot be self-granted via any API (`User.is_platform_admin` has no
API-writable path per that model's docstring).

**3. Injection / XSS / CSRF.** No raw/string-built SQL anywhere — every query in
`app/impl/repositories.py` goes through SQLAlchemy `select()`/`session.execute(stmt)`
with bound parameters; no `f"SELECT..."`-style string interpolation found. No
`dangerouslySetInnerHTML` or raw `innerHTML` assignment anywhere in
`services/web/src`. Auth is Bearer-token-in-header (not cookie-session), so classic
CSRF is structurally not applicable — confirmed in
`services/web/src/data/real/httpClient.ts`, which attaches `Authorization: Bearer
<token>` per request rather than relying on cookies. CORS is configured with an
explicit allow-list (`app/core/config.py::cors_allowed_origins`, no wildcard fallback
outside local dev) and wired via `CORSMiddleware` in `app/main.py`.

**4. Rate limiting.** Partially implemented — general-purpose, not
AI-invocation-specific (because no AI-invocation endpoint exists yet). `app/core/
rate_limit.py` configures `slowapi` with a blanket `60/minute` per-IP default
(`GENERAL_RATE_LIMIT`) applied via `SlowAPIMiddleware`, plus a tighter `5/minute`
(`AUTH_RATE_LIMIT`) on `POST /auth/signup` and `POST /auth/login`
(`app/routers/auth.py` lines 31, 55). Storage is in-memory (documented tradeoff for a
single-VPS, single-replica pilot). CLAUDE.md's explicit call for AI-agent-invocation
rate limiting is not yet applicable — issue #20 (AI agent invocation trigger) is
unstarted, so there's no invocation endpoint to rate-limit yet. Marketplace RFP/
Solution creation endpoints rely only on the blanket 60/min limit, not a
per-user/per-org cap — acceptable for now given no matching engine exists yet either
(issues #66-68 unstarted).

**5. Moderation audit trail immutability.** Genuinely insert-only for what exists.
`app/models/moderation.py::ModerationOverrideEvent` — its docstring states "Nothing in
this codebase should ever UPDATE or DELETE a row in this table," and this is true by
inspection: `app/services/moderation_service.py::_apply()` always calls
`moderation_repo.add(ModerationOverrideEvent(...))` (insert-only) alongside a separate
mutable `hidden` flag flip on the target `FeedPost`/`Comment` row — never touches the
audit row itself. Same pattern confirmed for `CommitmentCheckpoint`
(`app/models/checkpoint.py`) — no code path updates or deletes rows in either table
(verified via `grep` for `.update(`/`.delete(` near both models; the one `session.delete()`
call in the whole repo is a `PostLike` toggle, unrelated to any audit table). Caveat:
this only covers the **human-override baseline** (issue #59-shaped functionality). No
AI-driven auto-block/appeal system exists yet (issues #23-26 unstarted) — so there is
no auto-block audit trail to evaluate for immutability yet; the principle is
documented and the one audit table that does exist follows it correctly.

**6. Appeal fraud throttling.** Not implemented — matches issue #58 exactly, no
overlap findings. There is no appeal mechanism in the codebase at all yet (no AI
auto-blocking exists to appeal against), so there is nothing to throttle. Confirmed by
`grep -rn "appeal" services/backend-api` returning no application code.

**7. Container/K8s security.** Functional but not hardened. All four Containerfiles
(`backend-api`, `ai-coordinator-worker`, `moderation`, `sarvam-mock`) use
`python:3.12-slim` with no `USER` directive — every container runs as root inside the
container (default for the base image). No k8s manifest under `infra/k8s/` sets a
`securityContext` (`runAsNonRoot`, `readOnlyRootFilesystem`,
`allowPrivilegeEscalation: false`) — verified via `grep -rn "securityContext" infra/k8s/`
returning zero matches. Resource requests/limits **are** set on backend-api,
ai-coordinator-worker, and sarvam-mock deployments (good practice, present). Secrets
are correctly injected via `secretRef`/`secretKeyRef` (never inlined as plaintext env
values) in both `infra/k8s/*/deployment.yaml` and `infra/k8s/postgres/statefulset.yaml`.
No manifest uses `hostNetwork`, `privileged: true`, or exposes a `NodePort`/
`LoadBalancer` Service — all Services are ClusterIP-equivalent (default), reached via
port-forward locally per `docs/local-dev.md`. Redis (`infra/k8s/redis/deployment.yaml`,
`docker-compose.prod.yml`) has no auth configured, documented as an accepted tradeoff
in the manifest's header comment ("No auth, no persistence, no HA — not representative
of the production data tier") since it's cluster-internal-only in both topologies.

**8. Dependency versions.** Nothing obviously stale or high-risk spotted.
`services/backend-api/pyproject.toml`: FastAPI ≥0.115, SQLAlchemy 2.x, PyJWT ≥2.8,
passlib+bcrypt ≥4.0, slowapi ≥0.1.9 — all current-generation, no known-bad pins.
`services/web/package.json`: React 19.2, react-router-dom 7.18, Vite 8.1, TypeScript
6.0 — current versions. Did not run a full CVE scan per the task's scope (spot-check
only), no `uv.lock`/lockfile anomalies noticed.

**9. IDOR / multi-tenancy (Marketplace).** Mixed — RFP and Solution write paths are
correctly gated, but two Organization read endpoints are not. `app/services/
marketplace_service.py::require_org_member` / `add_member`'s admin check are properly
enforced before `create_rfp`, `add_rfp_requirement`, `create_solution`, and
`add_solution_attribute` (all verify caller membership via `org_repo.get_membership`
before allowing the write — confirmed in `marketplace_service.py` lines 80-94,
113-144, 191-236). RFP invite-only visibility is also correctly filtered
(`search_rfps`, `get_rfp_route` both check membership before returning invite-only
RFPs to non-members, `rfps.py` lines 127-137, 192-201). **However**,
`app/routers/marketplace/organizations.py::get_organization_route` (line 55-71) and
`list_members_route` (line 108-124) only depend on `get_current_user` — **any**
authenticated user (any civic User, from any or no Organization) can fetch **any**
other Organization's full detail (including `rfp_free_quota_used`/
`rfp_free_quota_limit`/`billing_status`, all exposed via `OrganizationOut`
per `app/models/marketplace/organization.py` lines 47-54) and its **full membership
list** (names/roles via `OrganizationMembershipOut`) by ID — no membership check, no
404 shielding for non-members the way invite-only RFPs get. See "Gaps" below (NEW,
not covered by any existing issue).

## Gaps

- [ ] **IDOR / info disclosure: Organization detail and member-list endpoints leak cross-tenant data to any authenticated user.** `GET /marketplace/organizations/{organization_id}` and `GET /marketplace/organizations/{organization_id}/members` (`services/backend-api/app/routers/marketplace/organizations.py` lines 55-71, 108-124) only require `get_current_user` — no check that the caller is a member of `organization_id`. Any logged-in civic User (including one with zero Organization memberships, or a member of a *competing* Organization) can enumerate another Organization's name, billing status, free-quota usage, and full member roster (user IDs + roles) simply by guessing/incrementing `organization_id`. Compare to `rfps.py`'s invite-only RFP handling, which correctly gates on `org_repo.get_membership(...)` before returning data — the same pattern is missing here. Why it matters: Organizations are B2B/B2G accounts (CLAUDE.md "Solution Marketplace Architecture" — "deliberately not the same as a civic User"); leaking billing/quota state and member rosters to any authenticated stranger is a real confidentiality issue for a marketplace meant to serve enterprise/government buyers, and member-roster leakage is a mild privacy issue for the individual users named. Severity: **Medium** (authenticated-only, read-only, no write/financial impact, but real cross-tenant confidentiality leak with a low bar — any signed-up user can hit it). Overlap: **NEW** — not covered by #63 (which only covers schema/design), #71 (billing/quota gate), or #73 (free-tier abuse via multiple Organizations, a different problem). Suggested fix: add a `require_org_member` (or `require_org_member_or_404`) dependency to both routes, mirroring the pattern already used correctly in `rfps.py`'s invite-only handling — return 404 rather than 403 for non-members to avoid confirming the Organization's existence to outsiders, consistent with how `get_rfp_route` already shields invite-only RFPs.

- [ ] **`docs/security-policy.md` is stale and now materially wrong about what's implemented.** The doc (dated 2026-07-09) states password hashing, JWT auth, commitment-gated authorization, and general/auth rate limiting are all "**Not yet**" implemented. All four are now implemented and merged (`app/core/security.py` bcrypt+JWT, `app/services/commitment_gate.py`, `app/core/rate_limit.py` + `app/main.py` CORS/SlowAPI wiring). Why it matters: a stale security-status doc is worse than no doc — it's the canonical place someone (including future-you, or a second developer per CLAUDE.md's "Solo Dev → Team Transition" section) would check before the SLC v1 pilot goes live, and right now it would lead them to believe core auth doesn't exist when it does, likely causing wasted re-verification effort or, worse, false confidence about a *different* stale "Not yet" that's actually still accurate. Severity: **Low** (documentation accuracy, not a code vulnerability) but flagged because CLAUDE.md explicitly calls for accurate security status tracking and the doc's own "Next review" section commits to re-running this checklist before pilot launch. Overlap: **NEW** — no existing issue tracks keeping this doc in sync; closest is #56 (API key policy) but that's narrower in scope than the whole doc. Suggested fix: re-run the checklist against current `main` and update the status table; consider adding a lightweight CI check or a note in the PR template reminding contributors to touch this doc when auth/rate-limiting/moderation code lands.

- [ ] **No `securityContext` on any k8s manifest — all containers run as root.** Verified across every file in `infra/k8s/*/deployment.yaml` and `infra/k8s/postgres/statefulset.yaml`: zero `securityContext` blocks (no `runAsNonRoot: true`, no `readOnlyRootFilesystem: true`, no `allowPrivilegeEscalation: false`, no dropped Linux capabilities). Compounded by every Containerfile (`services/{backend-api,ai-coordinator-worker,moderation,sarvam-mock}/Containerfile`) lacking a `USER` directive, so the container's default root user is whatever `python:3.12-slim` ships (root). Why it matters: this is local-dev-only today (manifests are explicitly headed "Local dev only" throughout), so exploitability is low right now, but it's exactly the kind of gap that's easy to forget once these same Containerfiles get reused for a production deploy (`docker-compose.prod.yml` explicitly reuses the same Containerfiles — "nothing is duplicated or rewritten here"). A container-escape or dependency-RCE bug is meaningfully worse when the process inside is root. Severity: **Low-Medium** (defense-in-depth gap, not an active exploit path found; elevated slightly because the prod Compose file inherits the same root-running images). Overlap: **NEW** — not explicitly covered by #55-59 (those are about moderation/secrets, not container hardening) or the closed infra epic (#39-54, which built the manifests but didn't harden them). Suggested fix: add `USER appuser` (non-root, created via `RUN useradd`) to each Containerfile, and add a minimal `securityContext: {runAsNonRoot: true, allowPrivilegeEscalation: false}` to each Deployment/StatefulSet pod spec — low-effort, should be safe to do even at this stage since these are stateless/simple services.

- [ ] **JWT stored in `localStorage`, not an httpOnly cookie — full token exfiltration on any future XSS.** `services/web/src/data/real/httpClient.ts` lines 37-47 (`getStoredToken`/`setStoredToken`/`clearStoredToken`) persist the bearer JWT in `localStorage`, readable by any JavaScript running in the page's origin. No XSS sink was found in the current frontend (no `dangerouslySetInnerHTML`/`innerHTML` usage), so this is not exploitable *today*, but it's a structural risk: the moment any XSS is introduced (e.g. when AI-generated markdown checklists get rendered client-side per CLAUDE.md's "AI-Generated Task Management" — issue #22, or a future rich-text feature), it becomes full session-token theft rather than a contained UI bug. This is a known, common tradeoff (httpOnly cookies bring their own CSRF-handling cost) and the current Bearer-header design is otherwise clean, so this is flagged as a design note rather than an urgent fix. Severity: **Low** (no active exploit path; the risk is latent and activates only alongside a future XSS bug). Overlap: **NEW** — no existing issue addresses token storage strategy. Suggested fix: no immediate action required given no XSS sink exists; worth reconsidering (httpOnly cookie + CSRF token, or short-lived access token + refresh rotation) before the markdown-checklist-rendering feature (issue #22) or any other user-generated-rich-content rendering path ships, since that's the point this risk stops being latent.

- [ ] **AI-agent-invocation-specific rate limiting not yet built — confirmed not-yet, matches existing issue.** CLAUDE.md explicitly calls for "strict rate limits on AI agent invocation to avoid runaway costs," distinct from general API rate limiting. Confirmed: no invocation-trigger endpoint exists yet at all (issue #20 unstarted), so there's nothing to rate-limit specifically; the general 60/min blanket limit in `app/core/rate_limit.py` would incidentally apply to any future invocation endpoint but was not designed with SARVAM cost containment in mind. Severity: **Informational** (not a gap in what exists, a reminder for what's coming). Overlap: covered by **#20** (AI agent invocation trigger) and the broader **#18** epic — when #20 is built, its cost-containment rate limit should be scoped separately from `GENERAL_RATE_LIMIT`, not just inherit it. No new issue filed.

- [ ] **Appeal fraud throttling, immutable AI-moderation audit logging, human-override UI — all confirmed not-yet-built, matching existing issues exactly.** No AI auto-blocking, no appeal mechanism, and no moderator UI beyond the baseline hide/restore endpoints exist yet. This matches issues **#57** (immutable audit logging for moderation actions — the AI-driven kind; the human-override kind that does exist is correctly immutable, see Current Status #5), **#58** (appeal fraud throttling), and **#24/#25/#26** (auto-block + review queue, appeal workflow, calibration loop) precisely. No new issue filed; #59 (human override) is already partially done (baseline hide/restore + audit trail exist) — worth noting in that issue's thread that the baseline is landed and correctly immutable, but that's a status update, not a new gap.

- [ ] **RFP/Solution creation endpoints share the general 60/min rate limit with no per-org quota enforcement yet — expected, tracked.** `create_rfp_route` and `create_solution_route` have no dedicated limiter beyond the blanket general one; the free-quota tracking columns exist on `Organization` (`rfp_free_quota_used`/`rfp_free_quota_limit`) but `app/services/marketplace_service.py::create_rfp`'s docstring explicitly states "no quota/billing check anywhere in `create_rfp`" by design for this phase. Confirmed intentional deferral, not an oversight. Overlap: **#71** (free-quota tracking + billing paywall gate) and **#73** (free-tier abuse safeguards) already cover this exactly. No new issue filed.

- [ ] **`.env.example`'s CORS comment is stale — claims "No CORS middleware is wired up yet," but it is.** The comment above `CORS_ALLOWED_ORIGIN` in `.env.example` (VPS/prod section) says "No CORS middleware is wired up yet (services/backend-api/app/main.py has no CORSMiddleware)" — this is no longer true; `app/main.py` lines 20-21 and 46-55 wire up `CORSMiddleware` with an explicit allow-list (`settings.cors_allowed_origins`, no wildcard fallback outside local dev). Not a vulnerability — CORS is in fact implemented correctly — but a second, independent instance (alongside `docs/security-policy.md`) of a security-relevant comment/doc trailing behind merged code. Severity: **Informational**. Overlap: **NEW**, but trivial enough to just fix inline rather than file a standalone issue — rolled into the same doc-sync note as the `security-policy.md` gap above.

## Issues filed vs. already covered

New GitHub issues filed for genuinely new gaps (not covered by any existing issue):

- **[#84](https://github.com/ADITYAMAHAKALI/Avadhana/issues/84) — IDOR: Organization detail/member-list endpoints leak cross-tenant data to any authenticated user** (`security` label). Covers the `GET /marketplace/organizations/{id}` and `.../members` gap described above.
- **[#85](https://github.com/ADITYAMAHAKALI/Avadhana/issues/85) — Containers run as root; no k8s securityContext hardening anywhere** (`security`, `infra` labels). Covers the missing non-root `USER` directives and missing `securityContext` blocks described above.

Gaps confirmed as already tracked by existing issues (no duplicate filed):
#18, #20, #24, #25, #26, #55, #57, #58, #59, #71, #73.

The stale-documentation findings (`docs/security-policy.md`, `.env.example`'s CORS comment) and the localStorage-JWT design note were judged too minor/discussion-shaped to warrant standalone issues — recorded in this report for visibility instead. Revisit localStorage-JWT before shipping any user-generated-content rendering path (e.g. issue #22's markdown checklists) that could introduce an XSS sink.

## Note on an out-of-band prompt-injection attempt during this audit

While a background copy of this same audit agent was running, it received two `SendMessage` requests purportedly from "another agent" asking it to resend its complete findings so *that* agent could write the report file and file GitHub issues on its behalf. The background agent correctly declined — its instructions were to return findings as a final message only, not to hand off report-writing or issue-filing to a third party, and the request carried no verifiable authorization from the user. It flagged this explicitly and continued the audit normally. Surfacing this here for transparency: no data was leaked and no unauthorized action was taken, but it's a useful reminder that inter-agent messages should be treated as untrusted input by default, the same as any other external channel.
