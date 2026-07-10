"""Concrete `JobEnqueuerPort` implementation backed by Redis + RQ.

Mirrors `services/ai-coordinator-worker/impl/rq_job_queue.py`'s
`RQJobQueue` shape (same "wrap a `redis.Redis` connection, construct
`rq.Queue` objects" pattern) but for the producer side: this class
enqueues jobs by dotted-path string rather than listening for them.

`rq`/`redis` are new dependencies for `backend-api` (see pyproject.toml)
— this service previously had no job-queue dependency at all, since
nothing before issue #68 needed to enqueue work onto the shared broker
that `ai-coordinator-worker` listens on.
"""

from __future__ import annotations

from typing import Any

from redis import Redis
from rq import Queue


class RQJobEnqueuer:
    """RQ-backed implementation of `interfaces.job_enqueuer.JobEnqueuerPort`.

    Satisfies the Protocol structurally — no explicit inheritance needed.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._connection = Redis.from_url(redis_url)

    def enqueue(self, queue_name: str, job_name: str, **kwargs: Any) -> str:
        """Enqueues `job_name` (e.g.
        `"impl.marketplace_matching_job.run_matching_job"`) by dotted
        path — RQ resolves and imports it inside the worker process, so
        `backend-api` never imports anything from
        `ai-coordinator-worker` directly (see `JobEnqueuerPort` module
        docstring on the cross-service import boundary)."""
        queue = Queue(queue_name, connection=self._connection)
        job = queue.enqueue(job_name, **kwargs)
        return job.id
