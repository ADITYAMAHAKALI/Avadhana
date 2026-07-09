"""Avadhana AI Coordinator Worker — RQ worker with a real SARVAM AI client.

The worker listens on a single queue named "ai-coordinator" and processes
jobs enqueued onto it. In production, the Backend API (or a scheduled job,
per CLAUDE.md's "every 3-6 hours" cadence) will enqueue real coordination
jobs here. `ping_job` proves Redis/RQ connectivity; `sarvam_ping_job` proves
SARVAM AI connectivity (real API or local mock, per `SARVAM_USE_MOCK`).

Real summarization/checklist-generation/off-topic-detection prompts and job
logic are NOT implemented here — that's issues #20-23, built on top of the
`SarvamClientPort` wired up in this module.

This module is the composition root: it is the one place that constructs
concrete implementations (`impl.rq_job_queue.RQJobQueue`,
`impl.sarvam_client.HttpSarvamClient`) of the abstract ports
(`interfaces.job_queue.JobQueuePort`, `interfaces.sarvam_client.SarvamClientPort`)
and wires them in via constructor injection / module-level globals (the
latter only because RQ jobs are plain re-importable functions — see
`ping_job`'s docstring for why). Nothing else in this service should import
`redis`/`rq`/`httpx` directly — depend on the ports instead so backends can
be swapped later without touching callers.

Usage:
    python worker.py

Configuration:
    REDIS_URL — full Redis connection string (default: redis://localhost:6379/0)
    See `sarvam_config.py` for SARVAM-related env vars.
"""

from __future__ import annotations

import os

from impl.rq_job_queue import RQJobQueue
from impl.sarvam_client import HttpSarvamClient
from interfaces.job_queue import JobQueuePort
from interfaces.sarvam_client import ChatMessage, SarvamClientPort
from sarvam_config import resolve_sarvam_config

QUEUE_NAME = "ai-coordinator"
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


def run_worker(job_queue: JobQueuePort, queue_names: list[str]) -> None:
    """Start listening for jobs via the injected `JobQueuePort`.

    Kept separate from `main()` so tests can call this with a fake
    `JobQueuePort` without touching env vars or real Redis.
    """
    job_queue.listen(queue_names)


def main() -> None:
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

    run_worker(job_queue, [QUEUE_NAME])


if __name__ == "__main__":
    main()
