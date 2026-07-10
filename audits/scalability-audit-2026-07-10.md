# Scalability Audit — 2026-07-10

Scope: `services/backend-api`, `services/ai-coordinator-worker`, `services/moderation`,
`services/web`, `infra/k8s`, `docker-compose.prod.yml`, `docs/vps-deployment.md`,
`docs/testing-strategy.md`. Code-first — every finding below was verified by reading
source, not inferred from CLAUDE.md alone.

**Context that shapes this audit**: per `TODO.md`, the AI Coordination Layer (epic
`#18`) and the Solution Marketplace matching engine are both **explicitly deferred /
not-yet-sequenced product decisions**, not oversights — "AI Coordination Layer (#18)
in full ... more expensive to build than to do by hand at 5-10-problem scale." The
platform is currently pre-launch, targeting a single-VPS 5-10-problem pilot
(`docs/vps-deployment.md`). So several items below are "not implemented yet" rather
than "implemented badly" — flagged accordingly, and distinguished from real defects in
code that **is** live.

## Current Status

**Implemented and working:**
- Core commitment system (3-slot enforcement, 90-day lock, checkpoint audit trail) —
  `services/backend-api/app/services/commitment_service.py`, `checkpoint_service.py`.
  Correctly indexed on the hot-path columns that exist (`commitments.user_id`,
  `commitments.problem_id` both have single-column indexes per
  `migrations/versions/53bc84afb894_initial_schema.py`).
- Commitment-gated feed (posts/comments/likes), human-moderator override
  (hide/restore), Marketplace foundation (Organization/RFP/Solution CRUD, no
  matching yet).
- Job queue infra: RQ + Redis (`services/ai-coordinator-worker/impl/rq_job_queue.py`,
  `worker.py`) is wired up correctly as fire-and-forget infrastructure — the worker
  listens on a Redis-backed queue, decoupled from the request path. **However**, the
  only job that exists today is `ping_job`/`sarvam_ping_job` — no real
  summarize/checklist/off-topic job handlers exist yet (confirmed: `worker.py` docstring
  says "Real summarization/checklist-generation/off-topic-detection prompts and job
  logic are NOT implemented here — that's issues #20-23"). No backend-api endpoint
  enqueues anything onto this queue yet either. So the "AI invocation is async, not
  blocking" requirement is honored by omission — there's no synchronous SARVAM call in
  `backend-api` to begin with (confirmed via grep: SARVAM only appears in
  `rate_limit.py`'s comments and `security.py`, not in any router logic).
- Rate limiting exists at the API-general level via `slowapi`
  (`app/core/rate_limit.py`): 5/min on auth endpoints, 60/min general default,
  in-memory storage. Explicitly documented as a single-process tradeoff that "must
  move to a shared (e.g. Redis-backed) storage backend" once horizontally scaled —
  this is a known, intentional limitation, not an oversight.
- K8s manifests (local dev only) have resource `requests`/`limits` set on
  `backend-api` and `ai-coordinator-worker` Deployments (50m/64Mi requests,
  250m/256Mi limits). Postgres and Redis run as single-replica
  StatefulSet/Deployment, explicitly commented "not representative of the production
  data tier."

**Not implemented (by design, tracked elsewhere):**
- No `EmbeddingVector`, `MatchRun`, `SolutionMatch`, or `BillingEvent` models exist
  anywhere in `services/backend-api/app/models/` — grep for `pgvector`, `ivfflat`,
  `hnsw`, `EmbeddingVector`, `embedding_space` across the whole repo returns zero
  code hits (only CLAUDE.md prose). The matching engine (RRF fusion, embeddings
  provider, attribute-match scoring) described in CLAUDE.md is 100% unbuilt. This
  maps to existing open issues **#66 (attribute-match scoring)**, **#67 (embeddings
  provider integration)**, **#68 (RRF rank fusion)** — so "no pgvector index" isn't a
  missing-index bug, it's that the column doesn't exist yet.
- No `marketplace-matching` Redis queue exists (only `ai-coordinator`,
  `QUEUE_NAME = "ai-coordinator"` in `worker.py`) — because there's no matching job
  to enqueue onto it yet. The queue-isolation requirement in CLAUDE.md ("separate
  queue named `marketplace-matching` ... rather than sharing a queue in a way that
  lets marketplace load starve civic AI coordination") has nothing to violate yet,
  but also nothing enforcing it will exist until issue #68/#67 land — flagged below
  so it's not forgotten when that work starts.
- No AI-invocation trigger endpoint (moderator-invoked "run the coordinator now")
  exists, so there is also no per-invocation rate limit/quota on it yet — tracked by
  epic **#18** and its sub-issues (**#20** "AI agent invocation trigger" in
  particular).

## Gaps

### Database / query patterns (real code, real defects)

- [ ] **No pagination on any list/search endpoint — unbounded result sets on tables
  expected to grow.** Confirmed via `grep -n "limit|offset|paginat"` across
  `app/routers/*.py` and `app/routers/marketplace/*.py`: zero hits outside rate-limit
  code. Specifically:
  - `GET /problems` (`app/routers/problems.py:44-58`) → `SqlAlchemyProblemRepo.search`
    (`app/impl/repositories.py:67-85`) has no `LIMIT`/`OFFSET`, returns every matching
    row.
  - `GET /problems/{id}/posts` (`app/routers/feed.py:48-62`) and
    `GET /problems/{id}/posts/{id}/comments` (`feed.py:114-128`) — same pattern, no
    limit.
  - `SqlAlchemyRFPRepo.search` (`repositories.py:373-391`) and
    `SqlAlchemySolutionRepo.search` (`repositories.py:421-438`) — same, plus
    `SolutionRepo.search`'s `category_tag` filter is applied **in Python after
    fetching the full unfiltered result set** (`repositories.py:432-437`), not in SQL.
  - Impact: at pilot scale (5-10 problems) this is invisible. At even moderate scale
    (hundreds of problems, thousands of posts/comments, an active RFP/Solution
    marketplace) these become full-table scans returned in a single HTTP response —
    unbounded response size and unbounded memory/DB load per request. This is the
    single most universal, highest-leverage gap in the audit because it touches nearly
    every read endpoint in the system, civic and marketplace alike.
  - Severity: **Medium now, High at any real growth** — cheap to fix (add
    `limit`/`offset` query params + `LIMIT`/`OFFSET` in the repo methods) before it
    becomes an incident.

- [ ] **N+1 query pattern on feed and problem list endpoints.**
  - `list_posts_route` (`app/routers/feed.py:48-62`): for each post returned, issues a
    separate `user_repo.get_by_id(post.author_user_id)` **and** a separate
    `feed_repo.like_count(post.id)` query. 20 posts = 41 queries for one request.
  - `list_comments_route` (`feed.py:114-128`): same pattern, one `get_by_id` per
    comment.
  - `list_problems` (`app/routers/problems.py:44-58`): for each problem, a separate
    `commitment_repo.count_active_by_role_for_problem(p.id)` query (a `GROUP BY`
    query per problem, not batched).
  - None of these are wrong at 5-10 problems / a handful of posts. They become the
    dominant cost as feed/problem volume grows — should be batched (single query with
    a JOIN or an `IN (...)` + dict-lookup) before real usage.
  - Severity: **Medium** — correctness is fine, this is a latency/DB-load cliff as
    data volume grows, not a bug.

- [ ] **No composite indexes on the (column, status) pairs actually queried together.**
  `commitments` has single-column indexes on `user_id` and `problem_id`
  (`migrations/versions/53bc84afb894_initial_schema.py:59-60`), but the hot-path
  queries in `SqlAlchemyCommitmentRepo` (`repositories.py:101-150`) all filter on
  `(user_id, status)` or `(problem_id, status)` together —
  `count_active_for_user`, `get_active_for_user_and_problem`,
  `list_active_for_user`, `count_active_by_role_for_problem`. Postgres can use the
  single-column index and filter `status` at the row level, so this isn't broken, just
  suboptimal — a composite index (`user_id, status`) / (`problem_id, status`) would
  make these true index-only lookups instead of index-scan-then-filter as the
  `commitments` table grows into the tens/hundreds of thousands of rows.
  Severity: **Low now, worth doing alongside any future migration touching this
  table** — not urgent at pilot scale.

- [ ] **No connection pool sizing configured.** `app/db/session.py:24-25` calls
  `create_engine(settings.database_url, pool_pre_ping=True, future=True)` with no
  `pool_size`/`max_overflow`/`pool_timeout` — SQLAlchemy defaults apply (`pool_size=5`,
  `max_overflow=10`, i.e. 15 connections max per engine instance). Fine for a
  single-replica pilot; becomes a silent cap the moment `backend-api` is horizontally
  scaled (each replica gets its own pool, so N replicas × 15 could exceed
  Postgres's own `max_connections`, or conversely each replica may be
  under-provisioned relative to its share of traffic). No code path currently
  reads/sets these from `Settings`. Severity: **Low now** (single-replica
  deployment throughout), but worth wiring as an env-configurable knob before any
  horizontal-scaling work, so it doesn't have to be rediscovered under load.

### AI Coordination / job queue

- [ ] **No rate limiting or quota on AI agent invocation exists — but also no
  invocation trigger exists to rate-limit yet.** CLAUDE.md's "Rate limiting & quotas"
  requirement ("Set up strict rate limits on AI agent invocation to avoid runaway
  costs") has no implementation surface today because the trigger endpoint itself
  (issue **#20**, "AI agent invocation trigger") is unbuilt. Flagging this explicitly
  so the quota/backpressure requirement doesn't get silently dropped when #20 is
  picked up — it should ship with a rate limit from day one, not be retrofitted after
  a cost incident. This overlaps directly with existing issue **#20** and epic
  **#18** — no new issue needed, but recommend the #20 implementation include the
  rate-limit/quota requirement explicitly in its acceptance criteria.

- [ ] **Batch-vs-per-request summarization is unverifiable — no real job exists yet.**
  CLAUDE.md requires "Batch summarization and checklist generation in scheduled jobs,
  not per-request." There is currently no summarization/checklist code at all (only
  `ping_job`/`sarvam_ping_job` placeholders in `worker.py`), so there's nothing to
  audit for batching correctness yet. Covered by existing issues **#21**
  (Summarization generation) and **#22** (Markdown checklist generation) — worth a
  note there (not a new issue) that the batching requirement should be a stated
  acceptance criterion, since it would be easy to implement a naive per-request
  version first and never circle back.

### Marketplace matching engine

- [ ] **pgvector is entirely unimplemented — not just missing an index.** No
  `EmbeddingVector` model, no pgvector extension reference, no vector column anywhere
  in the codebase. This is squarely covered by existing issue **#67** ("Embeddings
  provider integration"). Flagging here only to make explicit for whoever picks up
  #67: when the `EmbeddingVector` table is created, it must ship with an `ivfflat` or
  `hnsw` index on the vector column from the *first* migration that creates it — a
  vector column with no ANN index degrades to sequential brute-force cosine-distance
  scans, which is the single most common pgvector production incident (fine at
  hundreds of rows, catastrophic at tens of thousands). Recommend adding this as an
  explicit acceptance-criterion note on issue #67 rather than assuming it'll be
  remembered later once the table exists and "works" on a small dev dataset.
  Severity: **High-if-forgotten** — the kind of gap that's invisible in dev/testing
  and only bites in production at scale, so it needs to be called out before the
  first version of that migration is written, not after.

- [ ] **`marketplace-matching` queue isolation is a design intent with nothing yet to
  isolate.** CLAUDE.md requires the matching job to run on a "distinctly-named
  `marketplace-matching` queue" separate from `ai-coordinator`, specifically so
  marketplace load can't starve civic AI coordination. Today only the
  `ai-coordinator` queue exists (`worker.py:41`); there's no matching job to place on
  a second queue yet, and no worker currently listens on more than one queue name.
  Covered by existing issue **#68** (RRF rank fusion / matching engine) — worth
  calling out there explicitly that `run_worker`/`main()` in `worker.py` will need to
  add `"marketplace-matching"` to its `listen()` queue list (or run a second worker
  process) rather than merging matching jobs onto the existing queue for convenience,
  since that would silently violate the isolation the architecture doc calls for.

### Infrastructure (local k8s dev + VPS pilot)

- [ ] **No HPA / autoscaling manifests anywhere in `infra/k8s/`.** All three
  Deployments/StatefulSet (`backend-api`, `ai-coordinator-worker`, `redis`) plus the
  `postgres` StatefulSet are hardcoded to `replicas: 1`, and no
  `HorizontalPodAutoscaler` resource exists in the repo. This is explicitly
  documented as "local dev only... not representative of production" in every
  manifest's header comment, and the actual production target today is
  `docker-compose.prod.yml` on a single VPS (also single-instance-per-service by
  design, per `docs/vps-deployment.md`'s explicit SLC v1 scoping). Not a bug for
  where the project is today, but worth a forward-looking note: neither the k8s
  manifests nor the VPS compose file have a scale-out story yet for when the pilot
  graduates past 5-10 problems. No existing issue directly tracks "add HPA
  manifests" — filed as new (see below), scoped narrowly to `ai-coordinator-worker`
  since that's the workload most likely to need elastic scaling first (job queue
  depth is a natural HPA signal via KEDA or a custom metric), rather than a vague
  "add autoscaling everywhere" ask.

- [ ] **Postgres and Redis are uncomplemented single points of failure in both
  environments.** `infra/k8s/postgres/statefulset.yaml` and
  `infra/k8s/redis/deployment.yaml` both run `replicas: 1` with no read replica, no
  backup CronJob (local dev), no Sentinel/cluster mode. `docker-compose.prod.yml`
  mirrors this (single `postgres`/`redis` container each) but at least has a
  documented daily `pg_dump` cron in `docs/vps-deployment.md` step 7 — Redis is
  explicitly and deliberately unpersisted ("queued jobs are transient, re-enqueued on
  the next scheduled AI coordinator run... acceptable trade for one fewer volume to
  back up during the pilot"). This is a reasonable, explicitly-reasoned tradeoff for
  an unvalidated 5-10-problem pilot per CLAUDE.md's "Database & Scaling for Solo Dev"
  guidance (managed DB service is the stated scale path, not yet reached). Not filing
  a new issue — this is pre-launch-appropriate risk acceptance, not an oversight, and
  `docs/vps-deployment.md` already flags "single-VPS pilot has no redundancy
  otherwise." Documented here for completeness per the audit's scope, not as an
  action item.

- [ ] **No caching layer for read-heavy paths (problem feed, marketplace browsing).**
  `GET /problems`, `GET /problems/{id}/posts`, `GET /rfps` (marketplace search) all
  hit Postgres directly on every request with no HTTP caching headers, no
  Redis-backed read cache, no CDN in front. Redis already exists in the stack (as the
  RQ broker) but nothing in `backend-api` currently uses it for caching — confirmed
  no `redis`/`cache` imports in `services/backend-api/app/`. At pilot scale this is
  a non-issue (low request volume, small dataset, direct Postgres reads are fast).
  Combined with the pagination gap above, this becomes relevant once problem/post
  volume and traffic both grow — the *personal, narrow* feed model in CLAUDE.md
  (each user only sees ≤3 committed problems) actually helps here, since there's no
  algorithmic global feed to cache expensively; problem-level feeds and marketplace
  search results are the more cacheable candidates. Filed as a new low-priority
  issue (see below) since no existing issue covers caching strategy.

## Filed Issues

New issues filed under the `scalability` label (all cross-referenced against the
~73 pre-existing issues first; overlapping gaps reference existing issues above
instead of duplicating):

- **#76** — Add pagination (limit/offset) to all list/search endpoints
- **#77** — Fix N+1 queries on feed and problem list endpoints
- **#79** — Add HPA manifest for ai-coordinator-worker (job-queue-depth-based scaling)
- **#80** — Add read-cache strategy for problem feed and marketplace browsing

Gaps already covered by existing issues (no duplicate filed, referenced inline
above instead): **#18/#20** (AI invocation trigger + quota), **#21/#22** (batched
summarization/checklist generation), **#67** (embeddings provider + pgvector
index), **#68** (RRF matching engine + `marketplace-matching` queue isolation).
