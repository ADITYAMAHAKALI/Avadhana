# VPS Deployment (SLC v1 Pilot)

Step-by-step guide to deploying Avadhana to a single VPS via Docker Compose,
for the SLC v1 pilot (5-10 real local problems). See `TODO.md`'s release
plan for why this is Compose-on-one-VPS and not Kubernetes: local dev uses
Kubernetes-via-Podman (`docs/local-dev.md`) deliberately for parity with a
future multi-node production target, but that complexity is disproportionate
for an unvalidated pilot. `docker-compose.prod.yml` reuses the exact same
per-service `Containerfile`s as local dev — nothing is rebuilt or forked.

See also `docs/security-policy.md` for the secrets/rotation policy this
runbook assumes, and `docs/testing-strategy.md` for what should be verified
before and after each deploy.

## 1. Provisioning assumptions

- A plain Ubuntu or Debian VPS (any provider — this doc makes no
  provider-specific assumptions: DigitalOcean, Hetzner, Linode, a bare
  machine, etc. all work identically from here).
- Docker Engine + the Docker Compose plugin installed (`docker compose
  version` should work — this doc uses the `docker compose` v2 CLI syntax,
  not the standalone `docker-compose` v1 binary). Follow Docker's official
  install instructions for your distro; not repeated here since it's
  provider/OS-version-specific and already well documented upstream.
- A non-root user in the `docker` group, so you don't need `sudo` for every
  compose command.
- Recommended minimum for the pilot's expected load (5-10 problems, small
  committed-member counts per problem): 2 vCPU / 4GB RAM / 40GB disk. Bump
  disk if you expect meaningful asset uploads (issue #33) once that lands.
- Firewall: only ports 22 (SSH), 80, and 443 need to be open to the public
  internet (see "Network topology" below). Everything else stays on the
  Compose-internal bridge network.
- A domain name pointed at the VPS's public IP, **if** you want TLS via the
  optional Caddy edge service (see below). Not required to bring the stack
  up initially — you can deploy without a domain and add TLS once one
  exists.

## 2. Network topology (read before exposing ports)

`docker-compose.prod.yml` does **not** publish `backend-api` or `web` on
host ports by default. Reasoning:

- `web`'s nginx (`services/web/nginx.conf`) only serves the built static
  frontend and its own `/healthz` — it does **not** reverse-proxy to
  `backend-api`. So "expose only web" is not sufficient on its own; the
  frontend's JS still needs a path to reach the API.
- The Security Checklist in `TODO.md` calls for "TLS/HTTPS terminated ... at
  the VPS reverse proxy (deployed)". A single edge process terminating TLS
  and proxying to both `web` and `backend-api` is the more production-correct
  shape than exposing each service on its own host port with no TLS.
- `docker-compose.prod.yml` includes an **optional, commented-out** `edge`
  service running Caddy, which gets automatic Let's Encrypt certificates for
  free when `CADDY_DOMAIN` is a real DNS name pointed at the VPS. This is
  commented out by default because there is no real domain to test it
  against yet at the time this file was written.

**Two supported modes:**

- **No domain yet (bring-up / early pilot testing):** leave `edge`
  commented out, and uncomment the `ports:` blocks on `web` (`8082:8082`)
  and, if you want to hit the API directly for debugging, `backend-api`
  (`8000:8000`). Traffic is plain HTTP — acceptable only for short-lived
  testing, not for real users submitting real commitments/PII.
- **Domain configured (real pilot launch):** set `CADDY_DOMAIN` and
  `CADDY_EMAIL` in `.env`, uncomment the `edge` service in
  `docker-compose.prod.yml`, create `deploy/Caddyfile` (sample below),
  re-comment the `ports:` blocks on `web`/`backend-api` so they're only
  reachable through Caddy, and open 80/443 (not 8000/8082) on the VPS
  firewall.

Sample `deploy/Caddyfile` (create this file yourself when enabling `edge` —
not included by default since it depends on your domain and route split):

```
{$CADDY_DOMAIN} {
    tls {$CADDY_EMAIL}

    handle /api/* {
        reverse_proxy backend-api:8000
    }

    handle {
        reverse_proxy web:8082
    }
}
```

Adjust the `/api/*` path prefix to match whatever the frontend is actually
configured to call once it's wired to a real backend (currently mock-data
backed per `TODO.md` — this is a forward-looking sample, not yet exercised
end-to-end).

**Open question for you:** whether `/api/*` (path-based split behind one
domain) or a separate `api.<domain>` subdomain is the better long-term
routing shape is a product/DNS decision, not something this doc decides —
either works with Caddy. Pick whichever the frontend team wires the base
URL to.

## 3. Configure environment variables

```
cp .env.example .env
```

Fill in **real production values** — do not reuse the local-dev defaults.
At minimum:

- `POSTGRES_PASSWORD` — a strong, unique value (not `changeme`).
- `JWT_SECRET` — a strong random value. Generate one with, e.g.:
  ```
  openssl rand -hex 32
  ```
- `DATABASE_URL` / `REDIS_URL` — **note these must point at the Compose
  service names (`postgres`, `redis`), not the k8s-internal hostnames used
  in `.env.example`'s committed defaults** (those are
  `postgres.avadhana-dev.svc.cluster.local` / `redis.avadhana-dev.svc.cluster.local`,
  which only resolve inside the local kind cluster). On the VPS, use:
  ```
  DATABASE_URL=postgresql://avadhana:<your-password>@postgres:5432/avadhana
  REDIS_URL=redis://redis:6379/0
  ```
- `SARVAM_USE_MOCK` — **keep this `true` for the SLC v1 pilot itself.**
  AI Coordination (SARVAM integration) is explicitly deferred per the SLC v1
  release plan in `TODO.md`; the pilot validates the core commitment
  mechanic first. Only flip to `false` (with a real `SARVAM_API_KEY`) once
  AI Coordination is un-deferred and the real SARVAM client integration
  (issue #19) has landed and been tested against the mock first.
- `CORS_ALLOWED_ORIGIN` — set to the real frontend origin (e.g.
  `https://avadhana.example.com`) once a domain exists; leave blank for
  bring-up testing over plain HTTP/IP.
- `CADDY_DOMAIN` / `CADDY_EMAIL` — only if enabling the optional `edge`
  service (see above).

`.env` must never be committed — see `docs/security-policy.md` for the full
secrets-handling policy.

## 4. Run database migrations

**Placeholder step** — the backend-api's migration tool/command is being
set up in parallel (see the Core Commitment System epic, `TODO.md` issues
`#4`-`#9`) and isn't landed yet as of this doc being written. Once it lands:

```
docker compose -f docker-compose.prod.yml run --rm backend-api alembic upgrade head
```

(assuming Alembic — CLAUDE.md's "Database & Scaling for Solo Dev" section
calls for migrations "from day one" via a tool like Alembic or Flyway, but
the exact command isn't verified yet.) **Verify the actual command in
`services/backend-api/README.md` once migrations land there before trusting
this snippet** — don't guess further than this placeholder.

Run migrations **before** starting `backend-api` on a fresh deploy (the
container will fail health checks against a schema-less database), and
**before restarting** `backend-api` on every redeploy that includes new
migrations (see "Rollback / redeploy" below for ordering).

## 5. Start the stack

```
docker compose -f docker-compose.prod.yml up -d --build
```

`--build` ensures each service rebuilds from its current `Containerfile` and
source rather than reusing a stale cached image — worth the extra time on a
low-traffic pilot VPS.

Watch startup:

```
docker compose -f docker-compose.prod.yml logs -f
```

## 6. Verify health

```
docker compose -f docker-compose.prod.yml ps
```

All services should show `healthy` (postgres, redis, backend-api,
sarvam-mock, web have healthchecks defined; ai-coordinator-worker has none —
same reasoning as `infra/k8s/ai-coordinator-worker/deployment.yaml`: no
lightweight RQ health command exists yet, check `docker compose logs
ai-coordinator-worker` instead).

Direct health endpoint checks (from the VPS, or from your machine if the
relevant port is temporarily published — see "Network topology"):

```
curl http://localhost:8000/healthz   # backend-api
curl http://localhost:8082/healthz   # web (nginx)
curl http://localhost:8080/healthz   # sarvam-mock (only if port temporarily exposed)
```

Through Caddy (once `edge` is enabled with a real domain):

```
curl https://<your-domain>/healthz
```

## 7. Backups

Postgres is the only service with a named volume (`postgres-data`) — see
`docker-compose.prod.yml`'s comment on why Redis is left unpersisted for
this pilot (it's only the RQ job-queue broker; queued jobs are transient and
re-enqueued on the next scheduled AI coordinator run).

Minimal daily `pg_dump` cron example (run on the VPS host, not inside a
container, so the dump survives even if the `postgres` container is
recreated):

```bash
# /etc/cron.daily/avadhana-pg-backup  (chmod +x)
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="/var/backups/avadhana"
mkdir -p "${BACKUP_DIR}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
cd /path/to/avadhana  # repo root, where docker-compose.prod.yml lives
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "${BACKUP_DIR}/avadhana-${TIMESTAMP}.sql.gz"
# Keep the last 14 daily dumps, prune older ones.
find "${BACKUP_DIR}" -name 'avadhana-*.sql.gz' -mtime +14 -delete
```

`POSTGRES_USER` / `POSTGRES_DB` need to be available to the cron
environment (source `.env` at the top of the script, or hardcode — cron
jobs don't inherit your shell's env by default). Copy backups off the VPS
periodically (e.g. to object storage) — a single-VPS pilot has no
redundancy otherwise; a disk failure without an off-box copy loses
everything.

Restore (for reference, not routine):

```
gunzip -c avadhana-<timestamp>.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"
```

## 8. Rollback / redeploy

```bash
git pull                                              # get latest code
docker compose -f docker-compose.prod.yml build       # rebuild changed images
# Run any new migrations BEFORE restarting backend-api (see step 4) —
# starting backend-api against an old schema with new migrations pending
# is fine (forward-compatible schema changes should be the norm - additive
# columns, not renames/drops, until you have a real migration-safety
# discipline in place), but running new backend-api CODE against an old
# schema will break if it expects new columns/tables to already exist.
docker compose -f docker-compose.prod.yml run --rm backend-api alembic upgrade head  # once migrations exist, see step 4
docker compose -f docker-compose.prod.yml up -d       # restart with new images
docker compose -f docker-compose.prod.yml ps          # confirm all healthy
```

**Rollback** (if a deploy breaks something): `git checkout <previous-good-sha>`,
rebuild, and redeploy following the same steps. Because this is a single-VPS
pilot with no blue/green or canary setup, rollback means brief downtime
while containers restart — acceptable at pilot scale, revisit before any
real growth push (see CLAUDE.md's "Growth tension" open issue — this
deployment shape is intentionally not built for scale).

**Migration rollback caveat:** rolling back application code does *not*
automatically roll back a migration that already ran. If a deploy included
a destructive migration (dropped/renamed a column) and you need to roll
back, you may need a corresponding down-migration or a restore from the
most recent `pg_dump` backup — decide this case-by-case once real migrations
exist; there's no generic safe answer here.
