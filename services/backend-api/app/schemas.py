"""Pydantic request/response models.

Kept in one flat module (not split per-resource) because the API
surface is still small; split into `app/schemas/*.py` if this file gets
unwieldy. Field names and shapes here are the literal API contract a
parallel frontend-wiring effort is coding against — do not rename fields
casually, the JSON shape (including camelCase aliases) must match
exactly.

camelCase on the wire, snake_case in Python: achieved via
`alias_generator` + `populate_by_name`, so route handlers/services work
with normal Python attribute names while `.model_dump(by_alias=True)`
produces the camelCase JSON the frontend expects.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

Role = Literal["thinker", "actor", "backer"]
Specialization = Literal[
    "Legal", "Research", "Content", "Web & app dev", "Ad campaign", "Field organizing"
]
Tier = Literal["S", "A", "B", "C", "D"]
CommitmentStatusOut = Literal["active", "resolved", "abandoned"]
CheckpointAction = Literal["resolve", "abandon", "continue"]
CheckpointEventOut = Literal["created", "resolved", "abandoned", "continued"]
HistoryStatus = Literal["resolved", "continued", "abandoned"]
ModerationTargetTypeOut = Literal["post", "comment"]
ModerationActionOut = Literal["hidden", "restored"]


class CamelModel(BaseModel):
    """Base for every response/request model: emits/accepts camelCase on
    the wire while keeping snake_case Python attribute names."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --- Auth -----------------------------------------------------------------


class SignupRequest(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    location: str = Field(default="", max_length=200)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class UserOut(CamelModel):
    id: str
    name: str
    initials: str
    location: str
    member_since: datetime
    reputation: int
    avatar_color: str


class AuthResponse(CamelModel):
    token: str
    user: UserOut


# --- Focus slots / committed problems / history ----------------------------


class FocusSlotsOut(CamelModel):
    used: int
    total: int


class CommittedProblemOut(CamelModel):
    problem_id: str
    role: Role
    specialization: Specialization | None
    day_in_cycle: int
    cycle_length_days: int
    next_task: str | None


class CommitmentHistoryOut(CamelModel):
    problem_title: str
    role: Role
    status: HistoryStatus
    note: str


# --- Problems ---------------------------------------------------------------


class ProblemCreateRequest(CamelModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=5000)
    location: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=100)
    tier: Tier


class ProblemOut(CamelModel):
    id: str
    title: str
    summary: str
    location: str
    category: str
    tier: Tier
    created_at: datetime
    # Hardcoded null: no problem hierarchy in SLC v1 (see CLAUDE.md scope
    # boundaries — parent/child pointers are explicitly deferred).
    parent_problem_title: None = None
    thinker_count: int
    actor_count: int
    backer_count: int
    # Hardcoded 0: no follow-tracking exists yet (deferred, same reason
    # as parent_problem_title).
    following_count: int = 0


# --- Commitments --------------------------------------------------------


class CommitmentCreateRequest(CamelModel):
    role: Role
    specialization: Specialization | None = None

    @field_validator("specialization")
    @classmethod
    def specialization_only_for_actor(cls, v: Specialization | None, info):
        role = info.data.get("role")
        if v is not None and role != "actor":
            raise ValueError("specialization must be null unless role is 'actor'")
        return v


class CommitmentOut(CamelModel):
    id: str
    problem_id: str
    role: Role
    specialization: Specialization | None
    status: CommitmentStatusOut
    started_at: datetime
    lock_expires_at: datetime
    created_at: datetime


class CheckpointRequest(CamelModel):
    action: CheckpointAction
    note: str | None = Field(default=None, max_length=1000)


class CheckpointOut(CamelModel):
    id: str
    commitment_id: str
    event_type: CheckpointEventOut
    occurred_at: datetime
    note: str | None


# --- Feed ---------------------------------------------------------------


class PostCreateRequest(CamelModel):
    body: str = Field(min_length=1, max_length=5000)


class FeedPostOut(CamelModel):
    id: str
    author_initials: str
    author_name: str
    author_color: str
    role_label: str
    time_ago: str
    body: str
    like_count: int


class CommentCreateRequest(CamelModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(CamelModel):
    id: str
    post_id: str
    author_initials: str
    author_name: str
    author_color: str
    role_label: str
    time_ago: str
    body: str


class LikeOut(CamelModel):
    like_count: int


# --- Moderation (issue #59: human moderator override baseline) ------------


class ModerationActionRequest(CamelModel):
    reason: str | None = Field(default=None, max_length=1000)


class ModerationOverrideEventOut(CamelModel):
    id: str
    target_type: ModerationTargetTypeOut
    target_id: str
    action: ModerationActionOut
    performed_by: str
    reason: str | None
    occurred_at: datetime


# --- Error payloads (documented shapes, not enforced via response_model
# on every route, since FastAPI's HTTPException detail is the transport) --


class SlotLimitExceededError(CamelModel):
    error: Literal["SLOT_LIMIT_EXCEEDED"] = "SLOT_LIMIT_EXCEEDED"
    message: str
    used: int
    total: int


class AlreadyCommittedError(CamelModel):
    error: Literal["ALREADY_COMMITTED"] = "ALREADY_COMMITTED"
    message: str


class LockActiveError(CamelModel):
    error: Literal["LOCK_ACTIVE"] = "LOCK_ACTIVE"
    message: str
    days_remaining: int


class NotCommittedError(CamelModel):
    error: Literal["NOT_COMMITTED"] = "NOT_COMMITTED"
    message: str
