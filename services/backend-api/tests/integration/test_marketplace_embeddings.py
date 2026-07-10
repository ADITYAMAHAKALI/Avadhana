"""Integration tests for `EmbeddingVector` persistence and the
`generate_and_store_embedding` service function (GitHub issue #67),
against the SQLite in-memory integration-test harness
(`tests/integration/conftest.py`).

Proves:
  - `EmbeddingVector` rows persist correctly (including the `vector`
    column's SQLite fallback path, `PortableVector` — see
    `app/models/marketplace/embedding.py`).
  - The insert-only contract: editing content (re-embedding the same
    owner+space with different text) produces a NEW row, never updates
    an existing one.
  - `generate_and_store_embedding` end-to-end against the mock client
    (no live API calls — `MockEmbeddingsClient` is deterministic and
    in-process).
"""

import pytest

from app.impl.embeddings_client_mock import MockEmbeddingsClient
from app.models.marketplace.embedding import EMBEDDING_DIMENSIONS, EmbeddingVector
from app.models.marketplace.organization import Organization
from app.models.marketplace.solution import Solution
from app.services.embeddings_provider import generate_and_store_embedding


def _make_solution(db_session) -> Solution:
    org = Organization(name="Provider Org")
    db_session.add(org)
    db_session.commit()

    solution = Solution(
        organization_id=org.id,
        title="Fleet Management Suite",
        description="Comprehensive vehicle tracking and maintenance scheduling.",
        category_tags=["logistics", "fleet"],
    )
    db_session.add(solution)
    db_session.commit()
    return solution


def test_embedding_vector_persists_with_correct_shape(db_session):
    solution = _make_solution(db_session)

    embedding = EmbeddingVector(
        owner_type="solution",
        owner_id=solution.id,
        embedding_space="summary",
        vector=[0.1] * EMBEDDING_DIMENSIONS,
        dimensions=EMBEDDING_DIMENSIONS,
        model_name="mock-embeddings-v1",
        model_version="",
    )
    db_session.add(embedding)
    db_session.commit()

    fetched = db_session.get(EmbeddingVector, embedding.id)
    assert fetched is not None
    assert fetched.owner_type == "solution"
    assert fetched.owner_id == solution.id
    assert fetched.embedding_space == "summary"
    assert len(fetched.vector) == EMBEDDING_DIMENSIONS
    assert all(isinstance(x, float) for x in fetched.vector)
    assert fetched.dimensions == EMBEDDING_DIMENSIONS
    assert fetched.generated_at is not None


def test_editing_content_produces_a_new_row_not_an_update(db_session):
    """The insert-only contract (module docstring on EmbeddingVector):
    re-embedding the same owner+space after a content edit must insert a
    NEW row and leave the old one completely untouched — never UPDATE in
    place."""
    solution = _make_solution(db_session)
    client = MockEmbeddingsClient(dimensions=EMBEDDING_DIMENSIONS)

    first = generate_and_store_embedding(
        db_session,
        owner_type="solution",
        owner_id=solution.id,
        text="Comprehensive vehicle tracking and maintenance scheduling.",
        space="summary",
        client=client,
    )

    # Simulate a content edit: same owner+space, different text.
    second = generate_and_store_embedding(
        db_session,
        owner_type="solution",
        owner_id=solution.id,
        text="Comprehensive vehicle tracking, maintenance scheduling, and fuel analytics.",
        space="summary",
        client=client,
    )

    assert first.id != second.id, "editing content must insert a new row, not update the old one"

    rows = (
        db_session.query(EmbeddingVector)
        .filter(
            EmbeddingVector.owner_type == "solution",
            EmbeddingVector.owner_id == solution.id,
            EmbeddingVector.embedding_space == "summary",
        )
        .all()
    )
    assert len(rows) == 2, "old row must be kept, not overwritten"

    # The old row's vector must be byte-for-byte unchanged after the
    # "edit" — proving no UPDATE ever touched it.
    still_there = db_session.get(EmbeddingVector, first.id)
    assert still_there is not None
    assert still_there.vector == first.vector

    # Different text -> different deterministic mock vector, confirming
    # the two rows aren't accidental duplicates of the same content.
    assert first.vector != second.vector


def test_generate_and_store_embedding_rejects_unknown_owner_type(db_session):
    client = MockEmbeddingsClient(dimensions=EMBEDDING_DIMENSIONS)
    with pytest.raises(ValueError):
        generate_and_store_embedding(
            db_session,
            owner_type="problem",  # not "rfp" or "solution"
            owner_id="some-id",
            text="irrelevant",
            space="summary",
            client=client,
        )


def test_same_owner_can_have_embeddings_in_multiple_spaces(db_session):
    solution = _make_solution(db_session)
    client = MockEmbeddingsClient(dimensions=EMBEDDING_DIMENSIONS)

    summary_embedding = generate_and_store_embedding(
        db_session,
        owner_type="solution",
        owner_id=solution.id,
        text="Comprehensive vehicle tracking and maintenance scheduling.",
        space="summary",
        client=client,
    )
    technical_embedding = generate_and_store_embedding(
        db_session,
        owner_type="solution",
        owner_id=solution.id,
        text="Comprehensive vehicle tracking and maintenance scheduling.",
        space="technical_spec",
        client=client,
    )

    assert summary_embedding.embedding_space == "summary"
    assert technical_embedding.embedding_space == "technical_spec"
    # Same text, different space -> different vectors (see
    # MockEmbeddingsClient._deterministic_vector docstring).
    assert summary_embedding.vector != technical_embedding.vector

    rows = (
        db_session.query(EmbeddingVector)
        .filter(
            EmbeddingVector.owner_type == "solution",
            EmbeddingVector.owner_id == solution.id,
        )
        .all()
    )
    assert len(rows) == 2
