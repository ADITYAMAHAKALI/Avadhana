# Free-Tier Deployment Plan

An alternative to `docs/vps-deployment.md` for standing up a real, publicly
reachable Avadhana deployment without paying for or provisioning a VPS.
Every service maps onto a free tier of a managed provider instead of a
single Docker Compose host. Same `Containerfile`s, same env var names as
`.env.example` — only *where* each service runs changes.

**Verify current limits before you commit to this plan.** Free-tier terms
(request limits, cold-start behavior, whether a credit card is required)
change frequently and are not something this doc can guarantee stays
accurate — treat the specific numbers below as "true as of when this was
written," not a permanent promise from each provider.

## 1. Service → provider mapping

| Service | Provider | Why |
|---|---|---|
| Postgres (+ pgvector) | **Neon** (neon.tech) | Free tier includes the `pgvector` extension (`CREATE EXTENSION vector` works out of the box), serverless — no server to manage, generous free storage/compute for a pilot's load. No credit card required to sign up. |
| Redis (RQ job-queue broker) | **Upstash** (upstash.com) | Free tier gives a real `redis://` TCP endpoint (not just a REST API), which is what `redis-py`/RQ need — drop-in replacement for the `REDIS_URL` this codebase already expects. No credit card required. |
| `backend-api` | **Render** (render.com) Free Web Service | Builds directly from `services/backend-api/Containerfile`, auto-HTTPS on a `*.onrender.com` subdomain, no domain purchase needed. Free tier spins the service down after ~15 min idle and cold-starts on the next request (a few seconds to ~1 min) — acceptable for a pilot, not for latency-sensitive production traffic. |
| `sarvam-mock` | **Render** Free Web Service | Same as above. Only needed while `SARVAM_USE_MOCK=true` (this plan's default — see below). |
| `web` (frontend) | **Render** Free Static Site | Static builds have no cold-start problem (they're just files behind a CDN, not a spun-down process) and Render's static-site tier is free and unrestricted in the way the web-service tier isn't. |
| `ai-coordinator-worker` | **GitHub Actions scheduled workflow** (`.github/workflows/`) | This is the one service that doesn't fit a free "web service" shape — it's currently a long-lived process that blocks forever listening on Redis (`Worker.work()`), and free web-service/cron tiers are generally built around either HTTP requests or paid background-worker plans. Instead of paying for that, or gambling on whether a given provider's free cron tier stays free, this runs the worker in **burst mode** (process whatever's currently queued, then exit) on a GitHub Actions `schedule:` trigger — free CI minutes cover this trivially (a few seconds per run, every few hours), and it matches CLAUDE.md's own framing of AI coordination as "invoked on-demand... every 3–6 hours," not a persistent process. |
| Moderation service | *(not deployed)* | Still a placeholder with no real logic and no manifest even in local k8s dev — consistent with `docker-compose.prod.yml`'s existing decision to leave it out until issue #18's off-topic detection actually lands. |

## 2. Burst mode (done)

`services/ai-coordinator-worker/worker.py`'s `run_worker()` used to call
`job_queue.listen(queue_names)`, which wraps RQ's `Worker.work()` and
**blocks forever** — it never returned after draining the queue, which a
scheduled GitHub Actions job needs to do. This has been implemented:

- `interfaces/job_queue.py`: `JobQueuePort.listen(...)` now takes `burst: bool = False`.
- `impl/rq_job_queue.py`: passes `burst=burst` through to RQ's own `worker.work(burst=burst)`.
- `worker.py`: reads a `--burst` CLI flag or `WORKER_BURST=true` env var and threads it through `main()` → `run_worker()`.
- `.github/workflows/ai-coordinator.yml`: the scheduled workflow itself (every 4 hours, plus manual `workflow_dispatch`), already added — see section 3d for the repo secrets it needs.

`burst` defaults to `False`, so local k8s dev and the VPS Compose plan
(`docs/vps-deployment.md`) are unaffected — this is purely additive.

## 3. Sign-up and key-retrieval steps

Do these in order — later steps need values (connection strings, secrets)
from earlier ones.

### 3a. Neon (Postgres)

1. Go to neon.tech → Sign up (GitHub OAuth is the fastest path, no card needed).
2. Create a new project — pick a region close to wherever Render ends up running (Render's free tier defaults to Oregon, US-West; picking a nearby Neon region cuts latency, though it's not critical for a pilot).
3. In the project dashboard, open **Connection Details**. Copy the connection string — it looks like:
   ```
   postgresql://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require
   ```
4. This codebase standardizes on the `psycopg` (v3) driver, not `psycopg2` — same fix `app/core/config.py` already applies for the VPS plan. Rewrite the scheme before using it as `DATABASE_URL`:
   ```
   postgresql+psycopg://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require
   ```
5. pgvector: Neon has the extension available but doesn't enable it by default. After migrations run once (step 5 below creates the `embedding_vectors` table via Alembic, which itself runs `CREATE EXTENSION IF NOT EXISTS vector`), you don't need to do anything manual — just confirm no permission error appears in the migration output. If it does, connect with `psql "<your-connection-string>"` and run `CREATE EXTENSION vector;` once by hand.

Save: the full `postgresql+psycopg://...` string as `DATABASE_URL`.

### 3b. Upstash (Redis)

1. Go to upstash.com → Sign up (GitHub OAuth works here too).
2. Create a new Redis database. Pick "Regional" (not "Global") — this codebase does simple request/response RQ operations, not the kind of multi-region fan-out Global is for, and Regional is simpler and free.
3. On the database's detail page, find **Connection** → copy the `redis://` (or `rediss://` for TLS) URL. It looks like:
   ```
   rediss://default:<password>@<host>.upstash.io:6379
   ```
4. Use `rediss://` (TLS) not `redis://` if both are offered — this URL crosses the public internet between Render/GitHub Actions and Upstash, unlike the VPS plan's Compose-internal bridge network.

Save: the `rediss://...` string as `REDIS_URL`.

### 3c. Render (backend-api, sarvam-mock, web)

1. Go to render.com → Sign up with GitHub, and grant Render access to this repo (`ADITYAMAHAKALI/Avadhana`) when prompted — this is what lets Render auto-deploy on push later.
2. Generate a `JWT_SECRET` locally before you start creating services (you'll paste it into two places' env vars — backend-api needs it to sign tokens):
   ```bash
   openssl rand -hex 32
   ```
   Save this value somewhere (password manager) — it's a secret, not something to commit.
3. **Create the `backend-api` Web Service:**
   - New → Web Service → connect the repo → set **Root Directory** to `services/backend-api`.
   - Render should detect the `Containerfile` automatically (Environment: Docker). If not, set it explicitly.
   - Plan: **Free**.
   - Environment variables (Render's dashboard → Environment tab) — set these, matching `.env.example`'s names. Note `backend-api` does **not** talk to SARVAM at all (only `ai-coordinator-worker` does — see step 3d) — it only needs the *embeddings* mock toggle for the Marketplace matching engine:
     ```
     ENVIRONMENT=production
     LOG_LEVEL=info
     DATABASE_URL=<from step 3a>
     JWT_SECRET=<generated above>
     CORS_ALLOWED_ORIGIN=<fill in after step 3e, once you know the web static site's URL>
     REDIS_URL=<from step 3b>
     EMBEDDINGS_USE_MOCK=true
     ```
   - Deploy. Render assigns a URL like `https://avadhana-backend-api.onrender.com` — note it down, you'll need it for the frontend and for CORS.
4. **Create the `sarvam-mock` Web Service:** same steps, **Root Directory** `services/sarvam-mock`, Plan Free, env vars `ENVIRONMENT=production` / `LOG_LEVEL=info`. Note its URL (e.g. `https://avadhana-sarvam-mock.onrender.com`) — you'll need it in step 3d as `SARVAM_MOCK_BASE_URL` for the GitHub Actions worker job (the only consumer of `sarvam-mock`; `backend-api` never calls it).
5. **Create the `web` Static Site:**
   - New → Static Site → same repo → **Root Directory** `services/web`.
   - Build Command: `npm run build` (confirm this matches `services/web/package.json`'s `build` script — it does, per this session's earlier work).
   - Publish Directory: `dist`.
   - Before the first build, add a Render Static Site environment variable `VITE_API_BASE_URL=<backend-api's Render URL>` (e.g. `https://avadhana-backend-api.onrender.com`) — Vite bakes `VITE_`-prefixed vars into the build at build time, so this must be set before the build runs, not after. Leaving it unset makes the app silently fall back to mock/fixture data (per `services/web/.env.example`), which will look like it's "working" but isn't touching your real backend.
   - Once deployed, note its URL (e.g. `https://avadhana-web.onrender.com`).
   - Go back to `backend-api`'s env vars and set `CORS_ALLOWED_ORIGIN=https://avadhana-web.onrender.com` (the exact static-site URL), then trigger a manual redeploy of `backend-api` so the new env var takes effect.

### 3d. GitHub Actions (ai-coordinator-worker)

The workflow file already exists (`.github/workflows/ai-coordinator.yml`) — you only need to add the secrets it reads:

1. In the repo (Settings → Secrets and variables → Actions → New repository secret), add:
   - `REDIS_URL` — same Upstash value as step 3b.
   - `DATABASE_URL` — same Neon value as step 3a (the marketplace-matching job writes to Postgres).
   - `SARVAM_USE_MOCK=true` and `SARVAM_MOCK_BASE_URL=<sarvam-mock's Render URL from step 3c.4>` — this is the only service that actually calls SARVAM/its mock.
2. The workflow runs on a `schedule:` cron (every 4 hours) plus `workflow_dispatch:` for manual runs, checks out the repo, installs `services/ai-coordinator-worker`'s dependencies, and runs `python worker.py --burst` with the secrets above injected as env vars.
3. No separate "key" to retrieve here — GitHub Actions scheduled workflows on your own repo are free (public repos: unconditionally; private repos: within GitHub's free monthly Actions-minutes allowance, which a few-seconds-per-run job every few hours won't come close to exhausting).

## 4. Run database migrations

From your local machine (with `uv` installed, same as local dev), point at the real Neon database and run migrations once, before the backend-api service handles any real traffic:

```bash
cd services/backend-api
DATABASE_URL="postgresql+psycopg://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require" \
  uv run alembic upgrade head
```

Re-run this (same command) after every future deploy that includes a new migration, same ordering rule as `docs/vps-deployment.md` step 4/8: migrate *before* the new backend-api code that depends on the new schema goes live.

## 5. Verify

```bash
curl https://<your-backend-api>.onrender.com/healthz
curl https://<your-web>.onrender.com/            # should serve the built frontend
```

Sign up a real account through the deployed frontend, commit to a test problem, and confirm the request round-trips through Render → Neon successfully. Expect the **first** request after idle time to be slow (cold start) — that's expected free-tier behavior, not a bug.

Once the worker's GitHub Actions workflow exists, trigger it manually once (`workflow_dispatch`) and check the run log for `pong` from `ping_job`/`sarvam_ping_job` (or real job output, once #20-23 land) to confirm it can actually reach Upstash.

## 6. What's different from the VPS plan

- No TLS setup needed — Render's `*.onrender.com` subdomains get free HTTPS automatically. No Caddy, no domain purchase, no `CADDY_DOMAIN`/`CADDY_EMAIL`.
- No backups step yet — Neon's free tier has its own retention/branching story (check their current docs for exact point-in-time-restore window on the free plan); this is not the same as the VPS plan's manual `pg_dump` cron and should be revisited once real user data exists.
- No `docker compose` — each service deploys independently through its provider's dashboard/CLI, triggered by pushes to `main` (Render auto-deploys on push by default once connected).
- Cold starts are a real UX cost on the free `backend-api`/`sarvam-mock` web services that the always-on VPS Compose stack doesn't have. Acceptable for validating the pilot; revisit before any real growth push (same "not built for scale" caveat CLAUDE.md's "Growth tension" section already applies to the VPS plan).
