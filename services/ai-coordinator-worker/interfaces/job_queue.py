"""Abstract port for the job-queue backend.

Defined as a `typing.Protocol` (PEP 544, structural typing) rather than an
`abc.ABC` base class — this avoids forcing concrete implementations into an
inheritance hierarchy just to satisfy the interface. Any object with a
matching `listen` method structurally satisfies `JobQueuePort`, DI-container
free.

This service is a plain RQ worker process (no HTTP framework), so there's no
`Depends()`-style mechanism to lean on the way the FastAPI services
(`backend-api`, `moderation`) do. Instead, `worker.py` acts as the
composition root: it constructs a concrete `JobQueuePort` implementation
(see `impl/rq_job_queue.py`) and passes it around via constructor injection.
"""

from __future__ import annotations

from typing import Protocol


class JobQueuePort(Protocol):
    """Minimal set of operations the composition root needs from a job-queue
    backend, independent of which library provides it (RQ today, potentially
    something else later).

    Deliberately narrow: it does not expose RQ's full `Queue`/`Worker`/
    `Connection` API surface, only what a caller of this service needs —
    start listening for jobs on a set of named queues and block until the
    process is stopped.
    """

    def listen(self, queue_names: list[str]) -> None:
        """Block and process jobs from the given queue names until stopped."""
        ...
