"""Resolve which SARVAM AI endpoint/credentials the worker should use.

Kept separate from `worker.py` so the `SARVAM_USE_MOCK` branching logic is
independently testable without touching env vars or constructing an actual
`HttpSarvamClient`.

Env vars (see `.env.example` and
`infra/k8s/ai-coordinator-worker/configmap.yaml`):
    SARVAM_USE_MOCK       — "true"/"false" (default "true"). When true,
                             requests go to the local sarvam-mock service
                             instead of the real SARVAM API — no live API
                             key required (see issue #51).
    SARVAM_MOCK_BASE_URL  — base URL for sarvam-mock, used only when
                             SARVAM_USE_MOCK is true.
    SARVAM_API_BASE_URL   — real SARVAM AI base URL, used only when
                             SARVAM_USE_MOCK is false.
    SARVAM_API_KEY        — real SARVAM AI API key, used only when
                             SARVAM_USE_MOCK is false. Required in that case.
    SARVAM_CHAT_MODEL     — default chat-completion model
                             (default "sarvam-105b").
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MOCK_BASE_URL = "http://sarvam-mock.avadhana-dev.svc.cluster.local:8080"
DEFAULT_REAL_BASE_URL = "https://api.sarvam.ai"
DEFAULT_CHAT_MODEL = "sarvam-105b"


@dataclass(frozen=True)
class SarvamConnectionConfig:
    base_url: str
    api_key: str
    default_model: str
    use_mock: bool


def resolve_sarvam_config(env: dict[str, str] | None = None) -> SarvamConnectionConfig:
    """Read env (or the given mapping, for tests) and resolve which SARVAM
    endpoint/credentials to use.

    Raises `ValueError` if `SARVAM_USE_MOCK` is false but no
    `SARVAM_API_KEY` is set — a live key is required outside mock mode
    (matches the check already enforced in `create-secrets.sh`).
    """
    source = env if env is not None else os.environ
    use_mock = source.get("SARVAM_USE_MOCK", "true").strip().lower() == "true"

    if use_mock:
        return SarvamConnectionConfig(
            base_url=source.get("SARVAM_MOCK_BASE_URL", DEFAULT_MOCK_BASE_URL),
            api_key="",
            default_model=source.get("SARVAM_CHAT_MODEL", DEFAULT_CHAT_MODEL),
            use_mock=True,
        )

    api_key = source.get("SARVAM_API_KEY", "")
    if not api_key:
        raise ValueError(
            "SARVAM_API_KEY is required when SARVAM_USE_MOCK is not 'true'. "
            "Set a real key in .env, or set SARVAM_USE_MOCK=true to use the "
            "local mock instead."
        )
    return SarvamConnectionConfig(
        base_url=source.get("SARVAM_API_BASE_URL", DEFAULT_REAL_BASE_URL),
        api_key=api_key,
        default_model=source.get("SARVAM_CHAT_MODEL", DEFAULT_CHAT_MODEL),
        use_mock=False,
    )
