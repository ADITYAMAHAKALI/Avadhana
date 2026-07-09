"""Abstract port for the SARVAM AI client.

Defined as a `typing.Protocol` (PEP 544, structural typing), matching the
convention already used by `interfaces/job_queue.py` in this service. Any
object with a matching `chat_completion` method structurally satisfies
`SarvamClientPort` — no inheritance required.

Scope (issue #19, "SARVAM AI client integration"): this is the low-level
transport client only — sending a chat-completion request to either the
real SARVAM AI API or the local mock (`services/sarvam-mock`) and returning
a normalized result. It does not implement summarization, checklist
generation, or off-topic detection prompts/logic themselves — those are
issues #20-23, built on top of this client.

Only `chat_completion` is exposed. SARVAM AI's public API
(https://docs.sarvam.ai/, verified against the live OpenAPI spec while
building this client) has no embeddings endpoint — unlike
`services/sarvam-mock`'s `/v1/embeddings`, which was scaffolded as a guess
before that could be verified. See `services/sarvam-mock/README.md`
"Assumptions & known gaps" for the corrected record. Semantic-similarity /
merge-conflict-detection work (CLAUDE.md's "AI Coordination Architecture")
will need a different strategy than SARVAM embeddings — not addressed by
this client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True)
class ChatCompletionResult:
    """Normalized result of a chat-completion call.

    Deliberately narrow — only what callers (summarization, checklist
    generation, off-topic detection) need. `raw` carries the full parsed
    JSON response for callers that need something not surfaced here
    (e.g. `tool_calls`), without forcing every field into this dataclass.
    """

    content: str
    model: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    raw: dict[str, Any] = field(default_factory=dict)


class SarvamClientPort(Protocol):
    """Minimal set of operations the composition root needs from a SARVAM AI
    client, independent of whether requests go to the real SARVAM API or the
    local mock (selected via `SARVAM_USE_MOCK`, see `worker.py`).
    """

    def chat_completion(
        self,
        *,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletionResult:
        """Send a chat-completion request and return a normalized result.

        `response_format` accepts SARVAM's structured-output shapes
        (`{"type": "json_object"}` or `{"type": "json_schema", ...}`) —
        useful for later off-topic-detection/checklist-generation callers
        that need reliably parseable output rather than free-form text.
        """
        ...
