"""Abstract port for the Marketplace's embeddings provider client.

Defined as a `typing.Protocol` (PEP 544, structural typing), mirroring
`services/ai-coordinator-worker/interfaces/sarvam_client.py`'s
`SarvamClientPort` convention exactly — any object with a matching
`embed`/`embed_batch` method structurally satisfies
`EmbeddingsClientPort`, no inheritance required.

Why this is a SEPARATE port/client from SARVAM (rather than extending
`SarvamClientPort`): SARVAM AI has no embeddings endpoint at all (see
CLAUDE.md "Model Stack & Inference" and
`services/ai-coordinator-worker/interfaces/sarvam_client.py`'s module
docstring — verified against SARVAM's live API reference while building
that client). CLAUDE.md "Solution Marketplace Architecture" ->
"Embeddings provider" makes this an explicit architectural decision:
bring in a *second*, independent embeddings provider used only for
Marketplace embeddings, alongside SARVAM for chat/summarization/
off-topic work elsewhere. This port is intentionally narrow — just
`embed`/`embed_batch` — so it says nothing about which concrete provider
answers it (see `app/impl/embeddings_client.py` for the real HTTP-backed
implementation, and `app/impl/embeddings_client_mock.py` for the
deterministic local/test stand-in).

`space` is threaded through even though most embeddings providers don't
have a native concept of "named space" — it's not sent to the provider
API at all (see `HttpOpenAIEmbeddingsClient.embed`), it only labels which
named `embedding_space` (CLAUDE.md: "summary", "technical_spec",
"industry_context", ...) the resulting vector is *for*, so
`generate_and_store_embedding` (`app/services/embeddings_provider.py`)
can pass it straight through onto the `EmbeddingVector.embedding_space`
column without every caller having to plumb it separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class EmbeddingResult:
    """Normalized result of an embed call.

    Deliberately narrow — only what
    `app/services/embeddings_provider.py` needs to populate an
    `EmbeddingVector` row. `raw` carries the full parsed JSON response for
    callers that need something not surfaced here, same convention as
    `interfaces.sarvam_client.ChatCompletionResult.raw`.
    """

    vector: list[float]
    model: str
    dimensions: int
    raw: dict[str, Any] = field(default_factory=dict)


class EmbeddingsClientPort(Protocol):
    """Minimal set of operations the composition root needs from an
    embeddings provider client, independent of whether requests go to
    the real provider or the deterministic mock (selected the same way
    SARVAM's mock is — see `app/services/embeddings_provider.py`).
    """

    def embed(self, *, text: str, space: str) -> EmbeddingResult:
        """Embed a single piece of text for the given named
        `embedding_space`. `space` is a label only (see module
        docstring) — it does not change how the text is embedded."""
        ...

    def embed_batch(self, *, texts: list[str], space: str) -> list[EmbeddingResult]:
        """Batch variant of `embed`. Implementations should prefer this
        over N sequential `embed` calls when embedding many texts for the
        same space (e.g. a future batch job) — the real HTTP
        implementation sends one request for the whole batch, matching
        OpenAI's embeddings API, which natively accepts a list of
        inputs."""
        ...
