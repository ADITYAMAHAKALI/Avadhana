"""Avadhana SARVAM AI Mock service.

Stands in for the real SARVAM AI API (https://docs.sarvam.ai/) during local
dev and CI, per CLAUDE.md ("SARVAM AI calls should be stubbable/mockable
locally so development and CI don't require live API credentials or burn
real cost.") and GitHub issue #51.

This is a pure canned/deterministic mock: no real ML, no external calls,
no live SARVAM credentials required. It exists so the real SARVAM client
(built later in issue #19) and the AI coordination code paths that depend
on it (summarization #20, checklist generation #21, off-topic detection
#22) have something locally reachable to point at, with a roughly
compatible request/response shape.

IMPORTANT: this mock's schema was verified against live SARVAM docs while
building the real client (issue #19,
`services/ai-coordinator-worker/impl/sarvam_client.py`). Chat completions
match closely; the auth header name does NOT (`api-subscription-key`, not
`Authorization: Bearer` — this mock still accepts anything, real callers
should not rely on that). The `/v1/embeddings` endpoint below is
**mock-only** — SARVAM AI's real API has no embeddings endpoint at all.
See README.md "Assumptions & known gaps" for the full record.
"""

import hashlib
import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

SERVICE_NAME = "avadhana-sarvam-mock"
SERVICE_VERSION = "0.1.0"

EMBEDDING_DIMENSIONS = 384

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)


@app.get("/")
def root() -> dict:
    """Basic service identity payload."""
    return {"service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/healthz")
def healthz() -> dict:
    """Liveness/readiness probe for Kubernetes."""
    return {"status": "ok"}


# --- Chat Completions -------------------------------------------------


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    # Accept and ignore any other SARVAM/OpenAI-shaped fields (top_p,
    # stream, etc.) without erroring, since real callers may pass them.
    model_config = {"extra": "allow"}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
    """Canned, deterministic stand-in for SARVAM's chat-completions endpoint.

    Mimics the general (OpenAI-compatible-ish) chat-completion response
    shape: a top-level `choices` list containing a `message` with `role`
    and `content`. Good enough for local dev/CI to exercise summarization,
    checklist-generation, and off-topic-detection code paths without
    hitting real SARVAM. No actual language model is invoked.
    """
    last_user_content = ""
    for message in reversed(request.messages):
        if message.role == "user":
            last_user_content = message.content
            break
    if not last_user_content and request.messages:
        last_user_content = request.messages[-1].content

    reply = (
        f"[MOCK RESPONSE] Received {len(request.messages)} message(s), "
        f"echoing last: {last_user_content}"
    )

    now = int(time.time())
    prompt_tokens = sum(len(m.content.split()) for m in request.messages)
    completion_tokens = len(reply.split())

    return {
        "id": f"mock-chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": now,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


# --- Embeddings ---------------------------------------------------------


class EmbeddingsRequest(BaseModel):
    input: str | list[str]
    model: str | None = Field(default="mock-embedding-model")
    model_config = {"extra": "allow"}


def _deterministic_vector(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    """Derive a fixed-length pseudo-random vector seeded from `text`'s hash.

    Deterministic: the same input string always produces the same vector,
    which is what matters for locally testing similarity / merge-conflict
    detection logic later (issue #18 area) — not real semantic meaning.
    """
    vector: list[float] = []
    counter = 0
    while len(vector) < dimensions:
        digest = hashlib.sha256(f"{text}:{counter}".encode("utf-8")).digest()
        # Turn each pair of bytes into a float in roughly [-1.0, 1.0].
        for i in range(0, len(digest) - 1, 2):
            if len(vector) >= dimensions:
                break
            raw = (digest[i] << 8) | digest[i + 1]
            vector.append((raw / 65535.0) * 2.0 - 1.0)
        counter += 1
    return vector


@app.post("/v1/embeddings")
def embeddings(request: EmbeddingsRequest) -> dict[str, Any]:
    """Canned, deterministic stand-in for SARVAM's embeddings endpoint.

    Accepts a single string or a list of strings via `input`. Returns one
    fixed-length deterministic pseudo-random vector per input string, so
    repeated calls with the same text yield the same vector.
    """
    inputs = request.input if isinstance(request.input, list) else [request.input]

    data = [
        {
            "object": "embedding",
            "index": index,
            "embedding": _deterministic_vector(text),
        }
        for index, text in enumerate(inputs)
    ]

    total_tokens = sum(len(text.split()) for text in inputs)

    return {
        "object": "list",
        "model": request.model,
        "data": data,
        "usage": {
            "prompt_tokens": total_tokens,
            "total_tokens": total_tokens,
        },
    }
