"""Marketplace embeddings: provider selection + embed-and-store service
function (GitHub issue #67).

Two things live here:

1. `resolve_embeddings_client()` — picks the real
   `HttpOpenAIEmbeddingsClient` or the deterministic `MockEmbeddingsClient`
   based on `settings.embeddings_use_mock`, mirroring
   `services/ai-coordinator-worker/sarvam_config.py`'s
   `resolve_sarvam_config` exactly (same "raise if mock is off but no key
   is set" behavior, same env-driven selection). Kept as a plain function
   here rather than a FastAPI `Depends()` provider because nothing calls
   it yet outside tests — no router or job wires this port up in this
   pass (see module docstring below on non-goals). The async matching job
   (#68) is expected to call this at worker-composition time, the same
   way `worker.py` calls `resolve_sarvam_config`.

2. `generate_and_store_embedding()` — the actual embed-and-persist
   service function a later phase's job will call. Takes an
   `EmbeddingsClientPort` (not a concrete client) as a parameter, same DI
   convention as every other `app/services/*.py` function taking repo
   ports — testable against the mock client with no real database or
   network call.

Explicit non-goals for this issue (per the build brief): this module is
NOT wired into RFP/Solution creation flows (`app/services/
marketplace_service.py`'s `create_rfp`/`create_solution` do not call
this) — auto-generating embeddings on every create belongs to the async
matching job in a later phase (#68). No RRF fusion, no MatchRun/
SolutionMatch, no cosine-similarity ranking logic lives here either.
"""

from __future__ import annotations

from app.core.config import settings
from app.impl.embeddings_client_mock import MockEmbeddingsClient
from app.interfaces.embeddings_client import EmbeddingsClientPort
from app.models.marketplace.embedding import EMBEDDING_DIMENSIONS, EmbeddingVector

_VALID_OWNER_TYPES = frozenset({"rfp", "solution"})


def resolve_embeddings_client() -> EmbeddingsClientPort:
    """Read `settings` and resolve which embeddings client to use.

    Raises `ValueError` if `embeddings_use_mock` is False but no
    `EMBEDDINGS_API_KEY` is set — a live key is required outside mock
    mode, matching `resolve_sarvam_config`'s identical guard for SARVAM.
    """
    if settings.embeddings_use_mock:
        return MockEmbeddingsClient(dimensions=EMBEDDING_DIMENSIONS)

    api_key = settings.embeddings_api_key
    if not api_key:
        raise ValueError(
            "EMBEDDINGS_API_KEY is required when EMBEDDINGS_USE_MOCK is not "
            "'true'. Set a real key in .env, or set EMBEDDINGS_USE_MOCK=true "
            "to use the deterministic mock instead."
        )
    # Imported lazily so importing this module (and running the mock path,
    # which is the default for tests/local dev) never requires httpx to be
    # configured for a real network call.
    from app.impl.embeddings_client import HttpOpenAIEmbeddingsClient

    return HttpOpenAIEmbeddingsClient(
        base_url=settings.embeddings_api_base_url,
        api_key=api_key,
        default_model=settings.embeddings_model,
    )


def generate_and_store_embedding(
    session,
    *,
    owner_type: str,
    owner_id: str,
    text: str,
    space: str,
    client: EmbeddingsClientPort,
) -> EmbeddingVector:
    """Embed `text` via `client` and persist a new `EmbeddingVector` row.

    Insert-only (see `app/models/marketplace/embedding.py` module
    docstring): calling this again for the same `(owner_type, owner_id,
    space)` after content changes writes a NEW row rather than updating
    any existing one — there is no update path in this function or
    anywhere else in this module.

    `session` is a plain SQLAlchemy `Session` (not a repo port) — unlike
    the rest of `app/services/*.py`, which routes all persistence through
    `app.interfaces.repositories` ports for fake-backed unit testability,
    this function has exactly one simple INSERT and no business-rule
    branching worth hiding behind a port yet. `SqlAlchemyEmbeddingVector
    Repo` can be added to `app/interfaces/repositories.py` /
    `app/impl/repositories.py` if/when a caller needs it unit-tested
    against a fake (e.g. the matching job in #68) — not needed for this
    issue's scope, where the persistence behavior is exercised directly
    against the SQLite integration-test harness instead.

    Raises `ValueError` for an unrecognized `owner_type` — fail fast
    rather than silently writing an unqueryable row.
    """
    if owner_type not in _VALID_OWNER_TYPES:
        raise ValueError(
            f"Unknown owner_type {owner_type!r}; expected one of {sorted(_VALID_OWNER_TYPES)}."
        )

    result = client.embed(text=text, space=space)

    embedding = EmbeddingVector(
        owner_type=owner_type,
        owner_id=owner_id,
        embedding_space=space,
        vector=result.vector,
        dimensions=result.dimensions,
        model_name=result.model,
        model_version="",
    )
    session.add(embedding)
    session.commit()
    session.refresh(embedding)
    return embedding
