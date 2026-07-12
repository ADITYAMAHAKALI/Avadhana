"""Avadhana AI Coordinator Worker — RQ worker with a real SARVAM AI client.

The worker listens on two queues: "ai-coordinator" (AI coordination jobs)
and "marketplace-matching" (the Solution Marketplace's RRF matching
engine, issue #68 — see `impl/marketplace_matching_job.py`). In
production, the Backend API (or a scheduled job, per CLAUDE.md's "every
3-6 hours" cadence for AI coordination, or the Marketplace's "on RFP
publish" trigger) enqueues real jobs onto whichever queue applies.
`ping_job` proves Redis/RQ connectivity; `sarvam_ping_job` proves SARVAM
AI connectivity (real API or local mock, per `SARVAM_USE_MOCK`).

Real summarization/checklist-generation/off-topic-detection prompts and job
logic are NOT implemented here — that's issues #20-23, built on top of the
`SarvamClientPort` wired up in this module. The Marketplace matching job
(issue #68) IS implemented, in `impl/marketplace_matching_job.py`.

This module is the composition root: it is the one place that constructs
concrete implementations (`impl.rq_job_queue.RQJobQueue`,
`impl.sarvam_client.HttpSarvamClient`) of the abstract ports
(`interfaces.job_queue.JobQueuePort`, `interfaces.sarvam_client.SarvamClientPort`)
and wires them in via constructor injection / module-level globals (the
latter only because RQ jobs are plain re-importable functions — see
`ping_job`'s docstring for why). Nothing else in this service should import
`redis`/`rq`/`httpx` directly — depend on the ports instead so backends can
be swapped later without touching callers. `impl.marketplace_matching_job.
run_matching_job` is the one exception to the "module-level global" DI
pattern: it constructs its own SQLAlchemy engine lazily from
`DATABASE_URL` on first use (mirroring how it constructs nothing at
import time), since a plain top-level function has no `main()`-populated
global to receive an engine through, and a query-scoped engine per job
invocation is simpler than adding a second module-level global just for
this one job.

Usage:
    python worker.py            # persistent listen (local k8s dev, VPS Compose)
    python worker.py --burst    # process whatever's queued now, then exit
                                 # (a scheduled invocation, e.g. GitHub
                                 # Actions on a free-tier deploy — see
                                 # docs/free-tier-deployment.md)

Configuration:
    REDIS_URL — full Redis connection string (default: redis://localhost:6379/0)
    DATABASE_URL — Postgres connection string, required only when a
        marketplace-matching job actually runs (see db_config.py).
    WORKER_BURST — "true"/"false" (default "false"). Same effect as
        --burst, for invokers that can't pass CLI args.
    See `sarvam_config.py` for SARVAM-related env vars.
"""

from __future__ import annotations

import os
import sys

from impl.rq_job_queue import RQJobQueue
from impl.sarvam_client import HttpSarvamClient
from interfaces.job_queue import JobQueuePort
from interfaces.sarvam_client import ChatMessage, SarvamClientPort
from sarvam_config import resolve_sarvam_config

QUEUE_NAME = "ai-coordinator"
# Marketplace RRF matching (issue #68) — a second, distinctly-named
# queue on the SAME Redis broker (CLAUDE.md "Service boundaries": "same
# broker, a distinctly-named marketplace-matching queue"), not a second
# worker process. `impl.marketplace_matching_job.run_matching_job` is
# the job handler `backend-api`'s trigger endpoint enqueues by dotted
# path (see that service's app/interfaces/job_enqueuer.py for why a
# string path, not a direct import, crosses the service boundary).
MARKETPLACE_MATCHING_QUEUE_NAME = "marketplace-matching"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

# RQ re-imports this module by path to execute jobs in the worker process,
# so a job handler can't receive its SARVAM client via constructor
# injection the way `run_worker` receives its `JobQueuePort`. This
# module-level global, populated once in `main()`, is the narrowest way to
# make the client reachable from a plain top-level function like
# `sarvam_ping_job`. Real job handlers (#20-23) should follow the same
# pattern rather than constructing their own client.
_sarvam_client: SarvamClientPort | None = None


def ping_job() -> str:
    """Trivial placeholder job to prove the worker can receive and run jobs.

    Kept as a plain module-level function rather than a method behind an
    interface: RQ enqueues jobs by importable reference (module path +
    function name), which it later re-imports in the worker process to
    execute. A DI-wrapped instance method would not survive that
    serialize/re-import round trip without extra plumbing, so job *handlers*
    stay plain functions while the job-queue *infrastructure* (connecting,
    listening, dispatching) goes through `JobQueuePort`.

    Replace/extend with real jobs (summarize, generate_checklist,
    detect_off_topic, ...) once SARVAM AI integration lands (issues #19-27).
    """
    return "pong"


def sarvam_ping_job() -> str:
    """Round-trips a trivial chat-completion through the wired SARVAM client
    (real API or local mock, per `SARVAM_USE_MOCK`) to prove connectivity —
    the SARVAM-AI equivalent of `ping_job`. Not a real coordination job."""
    if _sarvam_client is None:
        raise RuntimeError("sarvam_ping_job called before main() wired up _sarvam_client")
    result = _sarvam_client.chat_completion(
        messages=[ChatMessage(role="user", content="ping")]
    )
    return result.content


def run_worker(job_queue: JobQueuePort, queue_names: list[str], burst: bool = False) -> None:
    """Start listening for jobs via the injected `JobQueuePort`.

    Kept separate from `main()` so tests can call this with a fake
    `JobQueuePort` without touching env vars or real Redis.
    """
    job_queue.listen(queue_names, burst=burst)


def _resolve_burst_flag(argv: list[str]) -> bool:
    """`--burst` on the command line, or `WORKER_BURST=true` in the
    environment (for platforms that invoke this as `python worker.py`
    with no way to pass extra CLI args, e.g. a scheduled CI job — see
    docs/free-tier-deployment.md). Either one is sufficient; neither is
    required, and the default (persistent listen) is unchanged."""
    if "--burst" in argv:
        return True
    return os.environ.get("WORKER_BURST", "false").strip().lower() == "true"


def main(argv: list[str] | None = None) -> None:
    # Redis/SARVAM connections are constructed here, inside main(), and
    # nowhere at module import time — this keeps `import worker`
    # side-effect-free (safe for tooling/tests) even without a reachable
    # Redis instance or SARVAM credentials.
    global _sarvam_client
    redis_url = os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)
    job_queue: JobQueuePort = RQJobQueue(redis_url=redis_url)

    sarvam_config = resolve_sarvam_config()
    _sarvam_client = HttpSarvamClient(
        base_url=sarvam_config.base_url,
        api_key=sarvam_config.api_key,
        default_model=sarvam_config.default_model,
    )

    burst = _resolve_burst_flag(sys.argv[1:] if argv is None else argv)
    run_worker(job_queue, [QUEUE_NAME, MARKETPLACE_MATCHING_QUEUE_NAME], burst=burst)


if __name__ == "__main__":
    main()
