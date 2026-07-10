"""Unit tests for the embeddings provider client (GitHub issue #67).

Mock implementation only for the determinism/contract tests — no live
API calls anywhere in this file. The real `HttpOpenAIEmbeddingsClient` is
exercised via `httpx.MockTransport` (same convention as
`services/ai-coordinator-worker/tests/test_sarvam_client.py`), which
still makes zero real network calls.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.impl.embeddings_client import DEFAULT_MODEL, HttpOpenAIEmbeddingsClient
from app.impl.embeddings_client_mock import MOCK_MODEL_NAME, MockEmbeddingsClient
from app.models.marketplace.embedding import EMBEDDING_DIMENSIONS


# --- MockEmbeddingsClient -----------------------------------------------


def test_mock_embed_is_deterministic():
    client = MockEmbeddingsClient(dimensions=64)
    a = client.embed(text="Fix the streetlight", space="summary")
    b = client.embed(text="Fix the streetlight", space="summary")
    assert a.vector == b.vector
    assert a.model == MOCK_MODEL_NAME


def test_mock_embed_has_fixed_dimensionality():
    client = MockEmbeddingsClient(dimensions=EMBEDDING_DIMENSIONS)
    result = client.embed(text="anything", space="summary")
    assert len(result.vector) == EMBEDDING_DIMENSIONS
    assert result.dimensions == EMBEDDING_DIMENSIONS
    assert all(-1.0 <= x <= 1.0 for x in result.vector)


def test_mock_embed_differs_by_text():
    client = MockEmbeddingsClient(dimensions=64)
    a = client.embed(text="Fix the streetlight", space="summary")
    b = client.embed(text="Fix the pothole", space="summary")
    assert a.vector != b.vector


def test_mock_embed_differs_by_space_for_same_text():
    """Same text embedded into two different named spaces must produce
    different vectors — see PortableVector/embed docstrings on why space
    is folded into the mock's hash seed."""
    client = MockEmbeddingsClient(dimensions=64)
    summary = client.embed(text="Same text", space="summary")
    technical = client.embed(text="Same text", space="technical_spec")
    assert summary.vector != technical.vector


def test_mock_embed_batch_matches_individual_embed_calls():
    client = MockEmbeddingsClient(dimensions=32)
    texts = ["first", "second", "third"]
    batch_results = client.embed_batch(texts=texts, space="summary")
    individual_results = [client.embed(text=t, space="summary") for t in texts]

    assert len(batch_results) == 3
    for batch_result, individual_result in zip(batch_results, individual_results):
        assert batch_result.vector == individual_result.vector


def test_mock_embed_batch_empty_list_returns_empty():
    client = MockEmbeddingsClient(dimensions=32)
    assert client.embed_batch(texts=[], space="summary") == []


# --- HttpOpenAIEmbeddingsClient (via httpx.MockTransport, no live calls) --


def _client(handler, **kwargs) -> HttpOpenAIEmbeddingsClient:
    return HttpOpenAIEmbeddingsClient(
        api_key="sk_test_key",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_embed_sends_expected_request_and_parses_response():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
                "model": DEFAULT_MODEL,
                "usage": {"prompt_tokens": 5, "total_tokens": 5},
            },
        )

    client = _client(handler)
    result = client.embed(text="Fix the streetlight", space="summary")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.openai.com/v1/embeddings"
    assert captured["headers"]["authorization"] == "Bearer sk_test_key"
    assert captured["body"] == {"model": DEFAULT_MODEL, "input": ["Fix the streetlight"]}

    assert result.vector == [0.1, 0.2, 0.3]
    assert result.model == DEFAULT_MODEL
    assert result.dimensions == 3


def test_embed_batch_sends_all_texts_in_one_request_and_preserves_order():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.2]},
                    {"index": 0, "embedding": [0.1]},
                ],
                "model": DEFAULT_MODEL,
            },
        )

    client = _client(handler)
    results = client.embed_batch(texts=["first", "second"], space="summary")

    assert captured["body"] == {"model": DEFAULT_MODEL, "input": ["first", "second"]}
    # Response arrived out of order (index 1 before index 0); client must
    # sort back into input order.
    assert [r.vector for r in results] == [[0.1], [0.2]]


def test_embed_batch_empty_list_makes_no_request():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("should not be called for an empty batch")

    client = _client(handler)
    assert client.embed_batch(texts=[], space="summary") == []


def test_embed_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    client = _client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.embed(text="hi", space="summary")


def test_no_auth_header_sent_when_api_key_is_empty():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.0]}], "model": DEFAULT_MODEL})

    client = HttpOpenAIEmbeddingsClient(
        api_key="", transport=httpx.MockTransport(handler)
    )
    client.embed(text="hi", space="summary")

    assert "authorization" not in captured["headers"]


def test_embed_uses_custom_model_override():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"data": [{"index": 0, "embedding": [0.0]}], "model": "custom-model"}
        )

    client = _client(handler, default_model="custom-model")
    client.embed(text="hi", space="summary")

    assert captured["body"]["model"] == "custom-model"
