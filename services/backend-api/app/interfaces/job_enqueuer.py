"""Abstract port for enqueuing background jobs onto the shared Redis/RQ
job-queue infrastructure that `services/ai-coordinator-worker` already
listens on.

Nothing in `backend-api` has ever needed to ENQUEUE an RQ job before this
(GitHub issue #68) — the analogous civic-side feature, issue #20 "AI
agent invocation trigger," is deferred post-v1 and unbuilt (see CLAUDE.md
"Invoking the AI Coordinator": still a TODO). This port is the first
producer-side piece of that infrastructure in this service.

Defined as a `typing.Protocol` (PEP 544, structural typing), same
convention as every other port in `app/interfaces/*.py` and mirroring
`services/ai-coordinator-worker/interfaces/job_queue.py`'s `JobQueuePort`
shape — but this is the mirror-image producer port (enqueue a job by
name), not the consumer port (listen for jobs) that service defines.
Deliberately narrow: `enqueue(queue_name, job_name, **kwargs)` is enough
for the Marketplace matching trigger endpoint's needs; it does not expose
RQ's full `Queue`/`Job` API.

`job_name` is a plain string (not a Python callable reference) because
the enqueuing process (`backend-api`) and the executing process
(`ai-coordinator-worker`) are separately-deployable services with no
shared Python import path between them — RQ's normal "enqueue a function
object, it pickles the reference" pattern only works when both sides can
resolve the same dotted path. Passing a string queue/job name (and letting
the impl construct the dotted path, e.g.
`"impl.marketplace_matching_job.run_matching_job"`) keeps `backend-api`
from needing to import anything from `ai-coordinator-worker` at all.
"""

from __future__ import annotations

from typing import Any, Protocol


class JobEnqueuerPort(Protocol):
    """Minimal set of operations `backend-api` needs to hand a job off
    to the shared Redis/RQ broker, independent of which library
    provides it (RQ today)."""

    def enqueue(self, queue_name: str, job_name: str, **kwargs: Any) -> str:
        """Enqueue `job_name` (a dotted path resolvable by whatever
        process listens on `queue_name`) with `kwargs`, returning the
        enqueued job's id (for logging/debugging — no caller in this
        pass polls job status by id, but returning it costs nothing and
        matches what RQ's own `enqueue_call` already returns)."""
        ...
