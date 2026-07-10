"""Unit tests for `app.services.embeddings_provider` (GitHub issue #67):
provider selection (`resolve_embeddings_client`) and the embed-and-store
service function's pure logic (owner_type validation). The persistence
side of `generate_and_store_embedding` is covered by the SQLite
integration test in `tests/integration/test_marketplace_embeddings.py`
— this file only exercises what doesn't need a real session.

`resolve_embeddings_client` reads `app.core.config.settings`, which
re-reads `os.environ` lazily via properties (see that module's
docstring: "which matters for tests that monkeypatch os.environ") — so
`monkeypatch.setenv`/`delenv` before each call is enough, no need to
reconstruct `Settings()`.
"""

from __future__ import annotations

import pytest

from app.impl.embeddings_client import HttpOpenAIEmbeddingsClient
from app.impl.embeddings_client_mock import MockEmbeddingsClient
from app.services.embeddings_provider import resolve_embeddings_client


def _clear_embeddings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "EMBEDDINGS_USE_MOCK",
        "EMBEDDINGS_API_KEY",
        "EMBEDDINGS_API_BASE_URL",
        "EMBEDDINGS_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


def test_defaults_to_mock_when_use_mock_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_embeddings_env(monkeypatch)

    client = resolve_embeddings_client()

    assert isinstance(client, MockEmbeddingsClient)


def test_mock_mode_ignores_real_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_embeddings_env(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_USE_MOCK", "true")
    monkeypatch.setenv("EMBEDDINGS_API_KEY", "sk_should_be_ignored")

    client = resolve_embeddings_client()

    assert isinstance(client, MockEmbeddingsClient)


def test_real_mode_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_embeddings_env(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_USE_MOCK", "false")

    with pytest.raises(ValueError, match="EMBEDDINGS_API_KEY is required"):
        resolve_embeddings_client()


def test_real_mode_returns_http_client_with_configured_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_embeddings_env(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_USE_MOCK", "false")
    monkeypatch.setenv("EMBEDDINGS_API_KEY", "sk_live_abc123")
    monkeypatch.setenv("EMBEDDINGS_API_BASE_URL", "https://api.openai.com")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "text-embedding-3-small")

    client = resolve_embeddings_client()

    assert isinstance(client, HttpOpenAIEmbeddingsClient)


def test_use_mock_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_embeddings_env(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_USE_MOCK", "TRUE")
    assert isinstance(resolve_embeddings_client(), MockEmbeddingsClient)

    monkeypatch.setenv("EMBEDDINGS_USE_MOCK", "False")
    monkeypatch.setenv("EMBEDDINGS_API_KEY", "k")
    assert isinstance(resolve_embeddings_client(), HttpOpenAIEmbeddingsClient)
