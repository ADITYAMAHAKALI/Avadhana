"""Deterministic, in-process mock implementation of `EmbeddingsClientPort`.

Exists so local dev and CI can exercise every code path that generates
and stores embeddings without live provider credentials or real cost —
the same rule CLAUDE.md already states for SARVAM ("SARVAM AI calls
should be stubbable/mockable locally") applied here to the second
embeddings provider (CLAUDE.md "Embeddings provider" decision).

Unlike SARVAM's mock (`services/sarvam-mock/`), this is NOT a standalone
HTTP service — it's a plain in-process fake implementation of the port,
directly analogous to how `services/ai-coordinator-worker`'s own tests
fake out `SarvamClientPort` by constructing a small stand-in object
rather than spinning up a server (see
`services/ai-coordinator-worker/tests/test_sarvam_client.py`, which uses
`httpx.MockTransport` for the *real* client's HTTP layer, not a second
process). A whole second FastAPI mock service would be disproportionate
ceremony here: this port has exactly two methods and no meaningfully
different request/response *shape* to fake at the wire level — the
in-process fake is what `app/services/embeddings_provider.py`'s
provider-selection function returns by default (mirroring
`SARVAM_USE_MOCK`), and it's what unit tests construct directly.

Determinism: the same `(text, space)` pair always produces the same
vector (seeded from a stable hash of the input), so tests can assert on
embedding output without brittle floating-point-equality-by-luck, and so
"editing content produces a NEW row with a DIFFERENT vector" is easy to
assert in the insert-only contract tests
(`tests/integration/test_marketplace_embeddings.py`). No real ML model
is invoked — this is not semantically meaningful, only shape-and-contract
compatible.
"""

from __future__ import annotations

import hashlib
import struct

from app.interfaces.embeddings_client import EmbeddingResult

MOCK_MODEL_NAME = "mock-embeddings-v1"
DEFAULT_MOCK_DIMENSIONS = 1536


class MockEmbeddingsClient:
    """Structurally satisfies `EmbeddingsClientPort` — no inheritance
    needed; Protocols use duck typing (PEP 544), same convention as
    every other impl in this codebase."""

    def __init__(self, dimensions: int = DEFAULT_MOCK_DIMENSIONS) -> None:
        self._dimensions = dimensions

    def embed(self, *, text: str, space: str) -> EmbeddingResult:
        return EmbeddingResult(
            vector=_deterministic_vector(text, space, self._dimensions),
            model=MOCK_MODEL_NAME,
            dimensions=self._dimensions,
            raw={"mock": True, "text_len": len(text), "space": space},
        )

    def embed_batch(self, *, texts: list[str], space: str) -> list[EmbeddingResult]:
        return [self.embed(text=text, space=space) for text in texts]


def _deterministic_vector(text: str, space: str, dimensions: int) -> list[float]:
    """Hash-of-text-based fake vector, fixed dimensionality.

    `space` is folded into the hash seed too (not just `text`) so the
    same text embedded into two different named spaces (e.g. "summary"
    vs. "technical_spec") deterministically produces two DIFFERENT
    vectors — matching real embedding providers, where per-space
    embeddings for the same content are typically produced by
    space-specific prompts/inputs rather than being identical.

    Expands a fixed-size hash digest into `dimensions` floats by
    repeatedly re-hashing (digest || counter), then normalizes each
    4-byte chunk into roughly the [-1, 1] range real embedding
    components fall in — good enough for shape/contract testing, not
    intended to carry any semantic meaning.
    """
    seed = f"{space}\x00{text}".encode("utf-8")
    values: list[float] = []
    counter = 0
    while len(values) < dimensions:
        digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        for i in range(0, len(digest) - 3, 4):
            if len(values) >= dimensions:
                break
            (raw_uint,) = struct.unpack(">I", digest[i : i + 4])
            # Map uint32 range onto [-1.0, 1.0].
            values.append((raw_uint / 0xFFFFFFFF) * 2.0 - 1.0)
        counter += 1
    return values
