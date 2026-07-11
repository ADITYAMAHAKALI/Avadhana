"""Problem-level resolution status (issue #100) — CLAUDE.md "Problem
Lifecycle Protocol".

Computes a `Problem`'s AGGREGATE resolution status by reading the
existing per-commitment checkpoint mechanism
(`app.models.checkpoint.CommitmentCheckpoint`,
`app.services.checkpoint_service`) rather than building a parallel
voting system. Compute-on-read, same pattern as
`CommitmentRepoPort.count_active_by_role_for_problem` — there is
deliberately NO materialized/cached status column on `Problem` that
would need separate invalidation logic. At this codebase's scale (a
handful of commitments and checkpoints per problem), recomputing on
every `GET /problems/{id}` is simpler and can never drift out of sync,
which is the same tradeoff the role-counts docstring on
`app.models.problem` already made explicitly for the same reason.

--- Status enum -------------------------------------------------------

Four values, matching `ProblemLifecycleStatus` in this module:
  - "open": below the resolution threshold — fewer committed members
    have claimed `resolved` (as their most recent checkpoint) than the
    threshold requires. The default/steady state for any active problem.
  - "pending_resolution": the threshold has been met (>= `_threshold`
    members have independently claimed resolved) and the 7-day
    objection window is still open, with no objection raised yet inside
    it. Will auto-flip to "resolved" once the window closes, or to
    "disputed" if an objection lands first.
  - "resolved": threshold met AND the 7-day window has closed (or is
    still open, functionally equivalent for status purposes — see
    `_window_closed` below) with zero objections raised inside it.
  - "disputed": threshold met, but at least one committed member raised
    an objection inside the 7-day window. Auto-resolution is blocked;
    the system does not auto-decide who's right — committed members
    work it out directly (per CLAUDE.md, "surfaces the disagreement for
    the group to work out directly").

Deliberately no "no committed members at all" special case beyond
"open" — a problem with zero committed members is trivially open (the
threshold, defined below, can never be met with zero members).

--- Threshold: ">= 2, or a strict majority, whichever is smaller" -----

CLAUDE.md's exact language: "at least 2 committed members, *or* a
strict majority of currently-committed members, whichever is the
smaller number, have independently marked their own commitment
resolved". Read literally as `min(2, majority(n))` this is ambiguous at
small `n`:
  - n=1: majority of 1 is 1 (>50% of 1 person is 1 person). `min(2, 1)`
    = 1. Literally, a SINGLE lone committed member's own resolve claim
    would satisfy the threshold. This directly contradicts the spec's
    stated intent (CLAUDE.md Known Unknown #3, now resolved) that
    resolution must "require more than one user's claim" — a lone
    claim is definitionally not independent corroboration.
  - n=2: majority of 2 is 2 (strict majority = more than half = > 1,
    so >= 2). `min(2, 2)` = 2. Unambiguous, matches intent.
  - n=3: majority of 3 is 2. `min(2, 2)` = 2. Unambiguous.
  - n>=4: majority keeps growing (>= 3 at n=5, etc.) so the floor of 2
    always wins: `min(2, majority(n))` = 2 for all n >= 2.

DECISION (this is the real judgment call the task brief asked for):
the ">= 2 members" clause is a HARD FLOOR, not just one arm of a min()
that can be undercut by a degenerate "majority of 1". The threshold
function is:

    threshold(n) = min(2, majority(n))   for n >= 2
    threshold(n) = infinity (unreachable) for n < 2

i.e. a problem with exactly 1 currently-committed member can NEVER
reach "resolved" or "pending_resolution" status through this mechanism
— there is no second independent claim possible, so corroboration is
structurally impossible, and the status stays "open" no matter what
that lone member's checkpoint says. This is the interpretation that
actually satisfies "more than one user's claim" at every value of n,
which is the one invariant CLAUDE.md is unambiguous about; a literal
`min(2, majority(n))` with no floor-on-n guard would violate it at
n=1, which would be a bug relative to intent, not a defensible reading
of the spec.

For n >= 2, `min(2, majority(n))` and `min(2, majority(n) if n >= 2)`
are identical (majority(2) = 2), so this only changes behavior at
exactly n=1 — nowhere else. Concretely: threshold is 2 for every n >=
2, since majority(n) >= 2 for all n >= 2 and the floor of 2 always
wins from n=4 upward anyway; the n=2 and n=3 cases are where "whichever
is smaller" actually matters (majority(2)=2, majority(3)=2 — both
equal to the floor, so the floor and the majority arm agree) — the
"whichever is smaller" clause only ever bites at n >= 4, where it caps
the requirement at 2 instead of demanding an ever-growing majority.

--- "Resolution claim episode" boundary --------------------------------

An "episode" is the span during which one particular set of `resolved`
claims accumulates toward the threshold and can be objected to. It is
NOT a stored concept (no `episode_id` anywhere) — it's derived at read
time from the data:

  1. Look at every currently-committed (non-abandoned, see
     `_CURRENTLY_COMMITTED_STATUSES` below) member's MOST RECENT
     checkpoint event for their commitment.
  2. The members whose most-recent event is `resolved` are the
     "resolved claimants" for the CURRENT episode.
  3. The episode's `window_start` is the EARLIEST `occurred_at` among
     those current resolved claimants' `resolved` checkpoints.
  4. The window is `[window_start, window_start + 7 days)`.

Why "most recent event" rather than "ever claimed resolved, ever":
`continue` and further checkpoints are possible on a commitment only
after the 90-day lock re-opens — but a commitment that has already
gone to RESOLVED or ABANDONED is terminal (see
`app.services.checkpoint_service`, "Terminal states never re-open").
So in practice, once a commitment's checkpoint history contains a
`resolved` event, that IS its most recent event, permanently — there
is no path back to `continue` after `resolved`. This means "most
recent event is resolved" and "has ever claimed resolved" collapse to
the same set FOR THE PURPOSES OF THIS COMPUTATION, given the current
checkpoint state machine. The "most recent event" framing is used
anyway (rather than "any resolved event ever") because it's the
correct general rule if the state machine ever grows a non-terminal
resolved-like state later, and it naturally excludes ABANDONED members
in the same pass (their most recent event is `abandoned`, not
`resolved`) without a separate filter.

Why "earliest among CURRENT claimants" rather than "earliest ever
across all history": this is what makes an old, already-closed episode
not haunt a future one. Example: two members resolve, no objection —
status becomes "resolved" (informational only, doesn't lock anything
per CLAUDE.md). A third member later joins... except commitment can't
be created after a problem is "resolved" in any special-cased way
(CLAUDE.md: "doesn't gate any other permission" — resolution status
never blocks new commitments). If a new member commits and later the
group decides to re-litigate (not really possible today since
RESOLVED commitments are terminal and can't un-resolve), the earliest
resolved-claim timestamp among CURRENTLY non-abandoned members is what
anchors the window — since resolved commitments never revert, in
practice every episode this computation will ever see is really just
"the one and only accumulation of resolved claims this problem has
had", but the derivation is written generally in terms of "current
claimants" rather than "first resolved checkpoint ever on this
problem" so it still behaves sensibly if a future change (e.g. an
early-exit/un-resolve path, explicitly NOT built here — see CLAUDE.md
Critical Open Issue #2) ever reopens a commitment.

--- Objections and the window -----------------------------------------

A `ResolutionObjection` counts toward the CURRENT episode if and only
if `window_start <= objection.raised_at < window_start + 7 days`. An
objection raised before the current window_start (from a prior,
already-closed episode — structurally near-impossible today given
terminal resolved commitments, but the rule is defined generally) or
after the window closed has NO effect on the current computation; the
row itself is never deleted (immutable audit trail, see
`app.models.resolution_objection`).

"One objection per user per episode" is enforced at write time in
`raise_objection()` below by checking whether the caller already has
an objection row with `raised_at` inside the current window — not by
a uniqueness constraint on the table (which has no natural per-episode
key to constrain against, since episodes aren't stored).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.core.time import utcnow
from app.interfaces.repositories import (
    CheckpointRepoPort,
    CommitmentRepoPort,
    ResolutionObjectionRepoPort,
)
from app.models.checkpoint import CheckpointEventType
from app.models.commitment import CommitmentStatus
from app.models.problem import Problem
from app.models.resolution_objection import ResolutionObjection
from app.services.errors import (
    AlreadyObjectedError,
    NoActiveResolutionWindowError,
    NotCommittedError,
)

OBJECTION_WINDOW = timedelta(days=7)

ProblemLifecycleStatus = Literal["open", "pending_resolution", "resolved", "disputed"]

# "Currently committed" for this computation = not abandoned. See module
# docstring's threshold/episode sections for why RESOLVED members still
# count (they're the ones making the claim) while ABANDONED members are
# excluded (someone who walked away doesn't corroborate or block).
_CURRENTLY_COMMITTED_STATUSES = {CommitmentStatus.ACTIVE.value, CommitmentStatus.RESOLVED.value}


@dataclass(frozen=True)
class ResolutionStatus:
    status: ProblemLifecycleStatus
    # Number of currently-committed members whose most recent checkpoint
    # is `resolved` — the "N" in "N/M claimed".
    resolved_count: int
    # Total currently-committed (non-abandoned) members — the "M" in
    # "N/M claimed".
    total_committed: int
    # min(2, majority(total_committed)) if total_committed >= 2, else
    # None (threshold unreachable with < 2 members — see module
    # docstring).
    threshold: int | None
    # Start of the current 7-day objection window — the earliest
    # `resolved` checkpoint among current claimants. None if no episode
    # is in progress (resolved_count == 0).
    window_start: datetime | None
    # window_start + 7 days. None under the same condition as
    # window_start.
    window_ends_at: datetime | None
    # Number of objections raised inside the current window. Always 0
    # when status == "resolved" or "open".
    objection_count: int


def _majority(n: int) -> int:
    """Strict majority of n: smallest integer > n/2."""
    return n // 2 + 1


def _threshold_for(total_committed: int) -> int | None:
    if total_committed < 2:
        # Structurally unreachable — see module docstring's threshold
        # section. A lone committed member's own claim is never
        # sufficient corroboration.
        return None
    return min(2, _majority(total_committed))


def compute_resolution_status(
    problem: Problem,
    *,
    commitment_repo: CommitmentRepoPort,
    checkpoint_repo: CheckpointRepoPort,
    objection_repo: ResolutionObjectionRepoPort,
    now: datetime | None = None,
) -> ResolutionStatus:
    now = now or utcnow()

    members = [
        c
        for c in commitment_repo.list_non_abandoned_for_problem(problem.id)
        if c.status in _CURRENTLY_COMMITTED_STATUSES
    ]
    total_committed = len(members)
    threshold = _threshold_for(total_committed)

    latest_checkpoints = checkpoint_repo.list_latest_for_commitments([c.id for c in members])

    resolved_claims: list[datetime] = []
    for member in members:
        latest = latest_checkpoints.get(member.id)
        if latest is not None and latest.event_type == CheckpointEventType.RESOLVED.value:
            resolved_claims.append(_as_aware(latest.occurred_at, now))

    resolved_count = len(resolved_claims)

    if threshold is None or resolved_count < threshold:
        return ResolutionStatus(
            status="open",
            resolved_count=resolved_count,
            total_committed=total_committed,
            threshold=threshold,
            window_start=None,
            window_ends_at=None,
            objection_count=0,
        )

    window_start = min(resolved_claims)
    window_ends_at = window_start + OBJECTION_WINDOW

    objections = [
        _as_aware(o.raised_at, now)
        for o in objection_repo.list_for_problem(problem.id)
        if window_start <= _as_aware(o.raised_at, now) < window_ends_at
    ]
    objection_count = len(objections)

    if objection_count > 0:
        status: ProblemLifecycleStatus = "disputed"
    elif now < window_ends_at:
        status = "pending_resolution"
    else:
        status = "resolved"

    return ResolutionStatus(
        status=status,
        resolved_count=resolved_count,
        total_committed=total_committed,
        threshold=threshold,
        window_start=window_start,
        window_ends_at=window_ends_at,
        objection_count=objection_count,
    )


def _as_aware(dt: datetime, now: datetime) -> datetime:
    """SQLite (integration tests) doesn't persist tzinfo; normalize
    before comparing so this works identically to Postgres — same
    pattern as `app.services.checkpoint_service._assert_lock_expired`."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=now.tzinfo)
    return dt


def raise_objection(
    *,
    problem: Problem,
    caller_user_id: str,
    commitment_repo: CommitmentRepoPort,
    checkpoint_repo: CheckpointRepoPort,
    objection_repo: ResolutionObjectionRepoPort,
) -> ResolutionObjection:
    """Records one objection for `caller_user_id` against the CURRENT
    resolution-claim episode on `problem`.

    Preconditions (all enforced here, in order):
      1. Caller must be a currently-committed member (ACTIVE or
         RESOLVED, i.e. not abandoned and not a stranger) — reuses the
         same "committed member" concept the status computation itself
         uses, NOT `require_committed_member`'s ACTIVE-only check,
         since a member who just resolved (and whose commitment is now
         terminal-RESOLVED) is exactly the kind of person who should be
         able to object to *other* members' resolve claims.
      2. There must be an active resolution window right now (status ==
         "pending_resolution" or "disputed" — i.e. threshold met and
         window not yet closed). Raises `NoActiveResolutionWindowError`
         otherwise (covers both "never claimed resolved" and "window
         already closed").
      3. Caller must not already have an objection inside the CURRENT
         window (one objection per user per episode — see module
         docstring). Raises `AlreadyObjectedError` otherwise.
    """
    members = [
        c
        for c in commitment_repo.list_non_abandoned_for_problem(problem.id)
        if c.status in _CURRENTLY_COMMITTED_STATUSES
    ]
    caller_commitment = next((c for c in members if c.user_id == caller_user_id), None)
    if caller_commitment is None:
        raise NotCommittedError(problem.id)

    status = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
    )
    if status.window_start is None or status.window_ends_at is None:
        # Either the threshold was never met (no claim to object to) or
        # — degenerate but handled — resolved_count regressed somehow.
        # Either way, there's nothing active to object to.
        raise NoActiveResolutionWindowError(problem.id)

    now = utcnow()
    if now >= status.window_ends_at:
        raise NoActiveResolutionWindowError(problem.id)

    existing = objection_repo.list_for_problem(problem.id)
    already_objected = any(
        o.objecting_user_id == caller_user_id
        and status.window_start <= _as_aware(o.raised_at, now) < status.window_ends_at
        for o in existing
    )
    if already_objected:
        raise AlreadyObjectedError(problem.id)

    return objection_repo.add(
        ResolutionObjection(problem_id=problem.id, objecting_user_id=caller_user_id)
    )
