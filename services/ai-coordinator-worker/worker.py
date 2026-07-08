"""Avadhana AI Coordinator Worker — minimal RQ worker skeleton.

This is a placeholder scaffold (see GitHub issue #43). It proves the job-queue
plumbing (Redis + RQ) works end to end, but does NOT yet implement any real
SARVAM AI integration (summarization, checklist generation, off-topic
detection). That work is tracked separately under issues #19-27.

The worker listens on a single queue named "ai-coordinator" and processes
jobs enqueued onto it. In production, the Backend API (or a scheduled job,
per CLAUDE.md's "every 3-6 hours" cadence) will enqueue real coordination
jobs here; for now the only job available is `ping_job`, used to verify
connectivity.

This module is the composition root: it is the one place that constructs a
concrete implementation (`impl.rq_job_queue.RQJobQueue`) of the abstract
`interfaces.job_queue.JobQueuePort` and wires it in via constructor
injection. Nothing else in this service should import `redis`/`rq` directly
— depend on `JobQueuePort` instead so the backend can be swapped later
without touching callers.

Usage:
    python worker.py

Configuration:
    REDIS_URL — full Redis connection string (default: redis://localhost:6379/0)
"""

from __future__ import annotations

import os

from impl.rq_job_queue import RQJobQueue
from interfaces.job_queue import JobQueuePort

QUEUE_NAME = "ai-coordinator"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


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


def run_worker(job_queue: JobQueuePort, queue_names: list[str]) -> None:
    """Start listening for jobs via the injected `JobQueuePort`.

    Kept separate from `main()` so tests can call this with a fake
    `JobQueuePort` without touching env vars or real Redis.
    """
    job_queue.listen(queue_names)


def main() -> None:
    # Redis connection is constructed here, inside main(), and nowhere at
    # module import time — this keeps `import worker` side-effect-free
    # (safe for tooling/tests) even without a reachable Redis instance.
    redis_url = os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)
    job_queue: JobQueuePort = RQJobQueue(redis_url=redis_url)
    run_worker(job_queue, [QUEUE_NAME])


if __name__ == "__main__":
    main()
