"""Concrete `EmbeddingsClientPort` implementation backed by OpenAI's
embeddings HTTP API.

Provider choice (CLAUDE.md "Embeddings provider": "OpenAI, Cohere, or a
self-hosted sentence-transformers model — final pick is an implementation
detail, not an architectural one"): OpenAI's `text-embedding-3-small` —
picked because it needs nothing beyond one HTTP call via `httpx` (already
a dependency of this service, see `pyproject.toml`'s `dev` extra and
`services/ai-coordinator-worker/impl/sarvam_client.py`'s identical
choice for SARVAM). Adding the `openai` Python package for a single
embeddings endpoint would be unnecessary SDK ceremony — this codebase's
existing pattern for third-party AI HTTP calls (see `HttpSarvamClient`)
is a small hand-rolled client, not a vendor SDK. `text-embedding-3-small`
also natively outputs 1536-dimensional vectors, matching
`EMBEDDING_DIMENSIONS` in `app/models/marketplace/embedding.py` and the
`pgvector` column's fixed dimensionality.

Mirrors `services/ai-coordinator-worker/impl/sarvam_client.py`'s shape
closely: a small class wrapping an `httpx.Client`, a `transport=` escape
hatch for tests to inject `httpx.MockTransport` instead of making real
network calls, and a `close()` method.

OpenAI embeddings API reference (https://platform.openai.com/docs/api-reference/embeddings):
  - Base URL: https://api.openai.com
  - Endpoint: POST /v1/embeddings
  - Auth header: `Authorization: Bearer <key>`
  - Request: {"model": ..., "input": <string | list[string]>}
  - Response: {"data": [{"embedding": [...], "index": 0}, ...], "model": ..., ...}
"""

from __future__ import annotations

import httpx

from app.interfaces.embeddings_client import EmbeddingResult

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 1536
DEFAULT_TIMEOUT_SECONDS = 30.0


class HttpOpenAIEmbeddingsClient:
    """HTTP-backed implementation of
    `interfaces.embeddings_client.EmbeddingsClientPort`.

    Satisfies the Protocol structurally — no explicit inheritance needed.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://api.openai.com",
        api_key: str,
        default_model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` is exposed only so tests can inject
        `httpx.MockTransport` instead of making real network calls —
        production callers should never pass it (same convention as
        `HttpSarvamClient`)."""
        self._default_model = default_model
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout_seconds,
            transport=transport,
        )

    def embed(self, *, text: str, space: str) -> EmbeddingResult:
        # `space` is a label only, not sent to the provider — see
        # interfaces.embeddings_client module docstring.
        return self.embed_batch(texts=[text], space=space)[0]

    def embed_batch(self, *, texts: list[str], space: str) -> list[EmbeddingResult]:
        if not texts:
            return []

        payload = {"model": self._default_model, "input": texts}
        response = self._client.post("/v1/embeddings", json=payload)
        response.raise_for_status()
        body = response.json()

        model = body.get("model", self._default_model)
        # OpenAI's response `data` entries carry an `index` field but are
        # already returned in input order; sort defensively rather than
        # assume that ordering holds across provider versions.
        data = sorted(body["data"], key=lambda item: item.get("index", 0))

        return [
            EmbeddingResult(
                vector=item["embedding"],
                model=model,
                dimensions=len(item["embedding"]),
                raw=body,
            )
            for item in data
        ]

    def close(self) -> None:
        self._client.close()
