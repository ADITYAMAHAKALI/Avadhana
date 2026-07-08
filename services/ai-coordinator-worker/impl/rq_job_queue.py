"""Concrete `JobQueuePort` implementation backed by Redis + RQ.

Wraps the `redis.Redis` connection and `rq.Queue`/`rq.Worker` construction
that used to live inline in `worker.py`'s `main()`. The composition root
constructs this class once (with a Redis URL) and injects it, via the
`JobQueuePort` interface, into whatever needs to start listening for jobs.
"""

from __future__ import annotations

from redis import Redis
from rq import Queue, Worker


class RQJobQueue:
    """RQ-backed implementation of `interfaces.job_queue.JobQueuePort`.

    Satisfies the Protocol structurally — no explicit inheritance needed.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._connection = Redis.from_url(redis_url)

    def listen(self, queue_names: list[str]) -> None:
        """Build RQ `Queue`s for `queue_names` and block on `Worker.work()`."""
        queues = [Queue(name, connection=self._connection) for name in queue_names]
        worker = Worker(queues, connection=self._connection)
        worker.work()
