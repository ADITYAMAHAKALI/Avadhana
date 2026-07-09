from __future__ import annotations

import json

import httpx
import pytest

from impl.sarvam_client import HttpSarvamClient
from interfaces.sarvam_client import ChatMessage


def _client(handler) -> HttpSarvamClient:
    return HttpSarvamClient(
        base_url="https://api.sarvam.ai",
        api_key="sk_test_key",
        transport=httpx.MockTransport(handler),
    )


def test_chat_completion_sends_expected_request_and_parses_response() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 1,
                "model": "sarvam-105b",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "hello back"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
        )

    client = _client(handler)
    result = client.chat_completion(
        messages=[ChatMessage(role="user", content="hello")],
        temperature=0.5,
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.sarvam.ai/v1/chat/completions"
    assert captured["headers"]["api-subscription-key"] == "sk_test_key"
    assert captured["body"] == {
        "model": "sarvam-105b",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.5,
    }

    assert result.content == "hello back"
    assert result.model == "sarvam-105b"
    assert result.finish_reason == "stop"
    assert result.prompt_tokens == 3
    assert result.completion_tokens == 2


def test_chat_completion_omits_unset_optional_fields() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "sarvam-105b",
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
                "usage": {},
            },
        )

    client = _client(handler)
    client.chat_completion(messages=[ChatMessage(role="user", content="hi")])

    assert captured["body"] == {
        "model": "sarvam-105b",
        "messages": [{"role": "user", "content": "hi"}],
    }


def test_chat_completion_uses_custom_model_override() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "sarvam-30b",
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
                "usage": {},
            },
        )

    client = _client(handler)
    client.chat_completion(
        messages=[ChatMessage(role="user", content="hi")], model="sarvam-30b"
    )

    assert captured["body"]["model"] == "sarvam-30b"


def test_chat_completion_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    client = _client(handler)

    with pytest.raises(httpx.HTTPStatusError):
        client.chat_completion(messages=[ChatMessage(role="user", content="hi")])


def test_no_auth_header_sent_when_api_key_is_empty() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(
            200,
            json={
                "model": "sarvam-105b",
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
                "usage": {},
            },
        )

    client = HttpSarvamClient(
        base_url="http://sarvam-mock:8080",
        api_key="",
        transport=httpx.MockTransport(handler),
    )
    client.chat_completion(messages=[ChatMessage(role="user", content="hi")])

    assert "api-subscription-key" not in captured["headers"]
