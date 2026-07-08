# AI Coordinator Worker

Minimal RQ (Redis Queue) worker skeleton for Avadhana's AI coordination layer
(see GitHub issue #43, epic #39). Listens on the `ai-coordinator` queue and
runs jobs. Currently only exposes a placeholder `ping_job` to prove the
Redis/RQ plumbing works — no real SARVAM AI integration yet (that lands in
issues #19-27).

## Build

```
podman build -t avadhana/ai-coordinator-worker -f services/ai-coordinator-worker/Containerfile services/ai-coordinator-worker
```

## Run

Requires a reachable Redis instance. Pass its URL via `REDIS_URL`
(defaults to `redis://localhost:6379/0` if unset):

```
podman run --rm -e REDIS_URL=redis://<redis-host>:6379/0 avadhana/ai-coordinator-worker
```

This is a placeholder skeleton pending real SARVAM integration and k8s wiring
(issues #19-27, #52).

## Dependency injection convention

This service follows the same interface/impl split as the other backend
services (`backend-api`, `moderation`), adapted to the fact that it's a
plain RQ worker process, not a framework app:

- `interfaces/` — abstract ports as `typing.Protocol` classes (structural
  typing, PEP 544), one file per interface, e.g. `interfaces/job_queue.py`
  defines `JobQueuePort`.
- `impl/` — concrete implementations, one file per implementation, e.g.
  `impl/rq_job_queue.py` defines `RQJobQueue`, wrapping the actual
  Redis/RQ connection and worker setup.
- `worker.py` is the **composition root**: the only place that constructs a
  concrete impl and wires it into the rest of the service via constructor
  injection (`RQJobQueue(redis_url=...)` passed in as a `JobQueuePort`).

Unlike `backend-api`/`moderation` (FastAPI apps, where dependencies are
injected per-request via `Depends()`), there's no HTTP framework here to
provide that mechanism — so injection here is done manually at process
startup instead of per-request. `ping_job()` stays a plain module-level
function rather than going behind an interface, because RQ dispatches jobs
by re-importing them by module path; see the comment on `ping_job` in
`worker.py` for details. When adding real SARVAM-backed job types (issues
#19-27), keep any external dependency they need (SARVAM client, DB access,
etc.) behind a `Protocol` in `interfaces/` with a concrete impl in `impl/`,
constructed in `worker.py` and passed in — don't reach for the concrete
library inline inside a job function.
