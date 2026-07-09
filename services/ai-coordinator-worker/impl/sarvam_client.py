"""Concrete `SarvamClientPort` implementation backed by SARVAM AI's HTTP API.

Works against either the real SARVAM AI API (https://api.sarvam.ai) or the
local mock (`services/sarvam-mock`) — both speak the same request/response
shape for `/v1/chat/completions`, so this one class serves both; the
composition root (`worker.py`) decides which `base_url`/`api_key` to
construct it with based on `SARVAM_USE_MOCK`.

Verified against SARVAM's live API reference (https://docs.sarvam.ai/) and
OpenAPI spec while building this client:
  - Base URL: https://api.sarvam.ai
  - Endpoint: POST /v1/chat/completions
  - Auth header: `api-subscription-key: <key>` (NOT `Authorization: Bearer`)
  - Models: `sarvam-30b` (64K context), `sarvam-105b` (128K context, flagship)
This confirms `services/sarvam-mock`'s endpoint path and request/response
shape were a good guess, but its (lack of) auth checking doesn't matter
locally either way, since the mock accepts any/no header.
"""

from __future__ import annotations

from typing import Any

import httpx

from interfaces.sarvam_client import ChatCompletionResult, ChatMessage

DEFAULT_MODEL = "sarvam-105b"
DEFAULT_TIMEOUT_SECONDS = 30.0


class HttpSarvamClient:
    """HTTP-backed implementation of `interfaces.sarvam_client.SarvamClientPort`.

    Satisfies the Protocol structurally — no explicit inheritance needed.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        default_model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` is exposed only so tests can inject `httpx.MockTransport`
        instead of making real network calls — production callers should
        never pass it."""
        self._default_model = default_model
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["api-subscription-key"] = api_key
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout_seconds,
            transport=transport,
        )

    def chat_completion(
        self,
        *,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletionResult:
        payload: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        response = self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        body = response.json()

        choice = body["choices"][0]
        usage = body.get("usage", {})
        return ChatCompletionResult(
            content=choice["message"]["content"] or "",
            model=body.get("model", payload["model"]),
            finish_reason=choice.get("finish_reason", "unknown"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw=body,
        )

    def close(self) -> None:
        self._client.close()
