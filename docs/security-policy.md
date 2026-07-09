# Security Policy (Pre-Launch)

Status tracking for Avadhana's security posture ahead of the SLC v1 pilot
deploy. This turns the security-relevant guidance already committed to the
repo — CLAUDE.md's "Security & Solo-Dev Architecture" section and the
"Security & Moderation Safety" epic (`TODO.md`, GitHub issue `#55`, sub-issues
`#56`-`#59`) — into a single point-in-time status document with an honest
done/not-yet/not-applicable call for each item, verified against what's
actually in the repo today (2026-07-09), not aspirational.

> **Note on sourcing:** this doc was scoped to restate a "Security Checklist
> (pre-launch)" section expected in `TODO.md`. As of this writing, `TODO.md`
> does not contain a section by that name — it has the "Security & Moderation
> Safety" epic (`#55`) with four sub-issues (`#56`-`#59`), which is what this
> doc tracks against instead. If a more detailed checklist gets added to
> `TODO.md` later, reconcile this doc against it rather than assuming this
> list is exhaustive — flagged here rather than inventing checklist items
> that aren't actually written down anywhere.

## Status legend

- **Done** — verified present in the repo as of this doc's last update.
- **Not yet** — not implemented; tracked against a specific issue.
- **N/A (for now)** — not applicable at the current stage (e.g. depends on a
  feature that doesn't exist yet), revisit when that feature lands.

## Secrets management

| Item | Status | Notes |
|---|---|---|
| `.env` excluded from version control | **Done** | `.gitignore` excludes `.env` and `.env.*`, explicitly allow-lists `.env.example` (`!.env.example`). Verified directly. |
| Local dev secrets via k8s Secrets | **Done** | `infra/k8s/scripts/create-secrets.sh` generates `avadhana-postgres-secret` / `avadhana-app-secret` from the local `.env`; script never echoes secret values to stdout/logs (verified in the script). |
| SARVAM API key never committed | **Done** | `.env.example` ships with `SARVAM_API_KEY=` blank; `SARVAM_USE_MOCK=true` is the default so no real key is needed for local dev/CI. |
| VPS/prod secrets management | **Not yet** | See "VPS secrets approach" below for the recommended interim approach — no VPS deploy has happened yet, so nothing to verify. |
| Key rotation policy (SARVAM key) | **Not yet** | See "SARVAM API key rotation" below for the documented policy; no rotation has occurred yet (no production key exists yet — `SARVAM_USE_MOCK=true` for the SLC v1 pilot itself). |
| API key & secrets management policy (issue `#56`) | **Not yet** | Tracked in the Security & Moderation Safety epic. This document is a first pass at that policy; formal issue not yet closed. |

### VPS secrets approach (recommended for this stage)

A dedicated secrets manager (Vault, cloud KMS, etc.) is overkill for a
solo-dev single-VPS pilot serving 5-10 problems — that complexity belongs in
a scale-up phase, not here. Recommended interim approach, consistent with
CLAUDE.md's "lighter-weight mechanism for a single dev machine" framing for
local dev:

- A root-level `.env` file on the VPS (never committed — same rule as local
  dev), readable only by the deploy user: `chmod 600 .env`, owned by that
  user, not world-readable.
- Docker Compose reads `.env` directly (`docker-compose.prod.yml`); no
  secret values appear in the compose file itself or in shell history if
  you avoid passing them as inline `-e` flags.
- SSH access to the VPS is itself the access-control boundary for who can
  read `.env` — keep the VPS's authorized SSH keys list minimal (realistically
  just the solo dev during the pilot phase).
- **Flag for later:** replace this with a real secrets manager (e.g. a
  managed KMS/secrets service) before any serious scale-up, team growth, or
  before handling real financial data at volume (the Donation flow, issue
  `#34`, is still an open design question and not yet built — revisit
  secrets posture before that ships).

### SARVAM API key rotation

- **Policy:** rotate the SARVAM API key on a regular cadence (recommend
  every 90 days, aligned with the platform's own commitment-cycle length as
  an easy-to-remember cadence — no functional dependency between the two,
  just a convenient shared reminder) and immediately if a leak is suspected
  (e.g. accidental commit, exposed log, compromised VPS).
  - Rotate: generate a new key in the SARVAM dashboard, update `.env` on the
    VPS, redeploy (`docker compose -f docker-compose.prod.yml up -d`,
    `backend-api` and `ai-coordinator-worker` both consume
    `SARVAM_API_KEY`), then revoke the old key once the new one is confirmed
    working.
- **Monitoring:** CLAUDE.md's "API Key & Secret Management" section calls
  for logging all AI API calls for auditing and cost tracking, and
  monitoring for unauthorized usage. Not yet implemented — no SARVAM client
  integration exists yet (issue `#19`, AI Coordination Layer epic `#18`,
  still unstarted; `SARVAM_USE_MOCK=true` everywhere today). Build this
  logging as part of `#19`, not as an afterthought.
- **This is currently moot for the SLC v1 pilot itself**, since
  `SARVAM_USE_MOCK` stays `true` through the pilot (AI Coordination is
  explicitly deferred — see `TODO.md`'s release plan and
  `docs/vps-deployment.md` step 3). Revisit this section for real once a
  production SARVAM key is provisioned.

## AI-call logging — no full user-data payloads

CLAUDE.md is explicit on this point; quoting it directly so this policy
doesn't drift from the source of truth:

> "Log all AI API calls (for auditing and cost tracking). Do not log the
> full request/response if it contains user data."

Current status: **N/A (for now)** — no SARVAM client exists yet to log
calls from (`SARVAM_USE_MOCK=true` everywhere, issue `#19` unstarted). This
constraint must be designed into the SARVAM client's logging from day one
when `#19` is built, not retrofitted — log metadata (timestamp, invocation
type, token/cost usage, confidence scores) and redact/omit full
request/response bodies containing user-submitted text.

## Auto-blocking & moderation safety

| Item | Status | Notes |
|---|---|---|
| Immutable audit logging for moderation actions (issue `#57`) | **Not yet** | No moderation logic exists yet (`services/moderation/` is a placeholder skeleton — just `/` and `/healthz`, per its README). Principle to build against when it lands: every auto-block, appeal, and appeal outcome logged with blocked message, confidence score, reason, appeal outcome, and any retraining triggered (CLAUDE.md "Auto-Blocking & Moderation Safety"). Records should be insert-only, never updated/deleted, consistent with the `CommitmentCheckpoint` audit-log pattern CLAUDE.md establishes elsewhere. |
| Appeal fraud throttling (issue `#58`) | **Not yet** | Tracked in the epic; no appeal mechanism exists yet to throttle. |
| Human override for moderators (issue `#59`) | **Not yet** | Tracked in the epic; no moderator role/UI exists yet. |
| Transparency (committed members can view moderation logs) | **Not yet** | Depends on the above landing first. |

This document intentionally does **not** propose new logging code or a
schema for these — that's implementation work for the Security & Moderation
Safety epic (`#55`) and the AI Coordination Layer epic (`#18`), which
depend on the moderation service actually existing first. This doc tracks
status only.

## Authentication & authorization

| Item | Status | Notes |
|---|---|---|
| Password hashing | **Not yet** | No auth/user code exists in `services/backend-api/` yet — verified by grep, no `password`/`hash`/`bcrypt`/`argon` references anywhere in the service. Tracked under Core Commitment System epic (`#3`), specifically "Design User schema" (`#4`). |
| JWT-based auth | **Not yet** | `JWT_SECRET` exists as a configured env var (`.env.example`, `infra/k8s/scripts/create-secrets.sh`) but is not yet consumed by any code — no JWT issuance/verification logic in `services/backend-api/app/` yet. |
| Commitment-gated authorization middleware (issue `#8`) | **Not yet** | Tracked under Core Commitment System epic. This is the mechanism enforcing "only committed members have voice" (CLAUDE.md's central anti-dilution rule) — high priority once basic auth lands. |
| Rate limiting (general API abuse) | **Not yet** | No rate limiting found anywhere in `services/` (verified by grep). CLAUDE.md's "Known Unknowns" flags this as an open question beyond AI-invocation rate limiting specifically. |
| AI agent invocation rate limiting | **Not yet** | CLAUDE.md calls for "strict rate limits on AI agent invocation to avoid runaway costs" — not yet built since no invocation trigger exists (issue `#20`). |

## Network / transport security

| Item | Status | Notes |
|---|---|---|
| TLS/HTTPS terminated at ingress (local) | **N/A (for now)** | Local k8s dev uses `kubectl port-forward` rather than an ingress controller (see `docs/local-dev.md` / `docs/dev-environment/podman-and-k8s.md` for the reasoning) — no TLS termination point exists locally by design; not a gap, a deliberate simplification for a single dev machine. |
| TLS/HTTPS terminated at the VPS reverse proxy (deployed) | **Not yet** | `docker-compose.prod.yml` includes an **optional, commented-out** Caddy `edge` service that gets automatic Let's Encrypt TLS once a real domain is pointed at the VPS (`CADDY_DOMAIN`/`CADDY_EMAIL` in `.env.example`). Not enabled by default — no domain exists yet to test it against. See `docs/vps-deployment.md` "Network topology" for the enable steps. This is real, working scaffolding, not yet exercised against a live domain. |
| Firewall (only 22/80/443 open) | **Not yet** | Documented as a provisioning step in `docs/vps-deployment.md`; no VPS has been provisioned yet to verify against. |

## Database & migrations

| Item | Status | Notes |
|---|---|---|
| Migrations tool from day one (Alembic/Flyway) | **Not yet** | No migration tooling found in `services/backend-api/` yet (no `alembic/` dir, no migrations dependency in `pyproject.toml`). Being set up by a parallel engineer per current project state; `docs/vps-deployment.md` step 4 is a placeholder pending this. |
| Immutable problem hierarchy / merge history | **N/A (for now)** | Problem Management & Hierarchy epic (`#10`) unstarted — nothing to verify yet. Principle already documented in CLAUDE.md ("never delete old relationships, only mark them inactive") to build against when it lands. |
| Postgres backups | **Not yet (documented)** | `docs/vps-deployment.md` includes a `pg_dump` cron example as a starting point; not yet exercised against a real deployed instance. |

## What's already solid

To be clear about what's actually working today, not just gaps:

- `.env` hygiene (gitignore, `.env.example` pattern, k8s Secrets sourcing)
  is correctly set up and consistently followed across local dev and this
  doc's VPS recommendations.
- The secrets-creation script (`infra/k8s/scripts/create-secrets.sh`) is
  careful not to leak values into logs/stdout — good precedent to follow
  when a VPS-equivalent script is eventually written (if one is; the
  simpler `.env` + Compose approach may not need one).
- SARVAM mocking (`SARVAM_USE_MOCK=true`, `services/sarvam-mock/`) means no
  real API credentials or cost exposure exists anywhere in the current
  system — there is currently no live external secret to leak, which is a
  meaningfully low-risk starting position.

## Next review

Re-run this checklist before the actual SLC v1 pilot goes live with real
users (not just before this scaffolding merges), and again before
`SARVAM_USE_MOCK` is ever flipped to `false` in production.
