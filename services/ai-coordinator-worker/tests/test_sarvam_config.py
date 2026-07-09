from __future__ import annotations

import pytest

from sarvam_config import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_MOCK_BASE_URL,
    DEFAULT_REAL_BASE_URL,
    resolve_sarvam_config,
)


def test_defaults_to_mock_when_use_mock_unset() -> None:
    config = resolve_sarvam_config({})

    assert config.use_mock is True
    assert config.base_url == DEFAULT_MOCK_BASE_URL
    assert config.api_key == ""
    assert config.default_model == DEFAULT_CHAT_MODEL


def test_mock_mode_ignores_real_api_key() -> None:
    config = resolve_sarvam_config(
        {"SARVAM_USE_MOCK": "true", "SARVAM_API_KEY": "sk_should_be_ignored"}
    )

    assert config.use_mock is True
    assert config.api_key == ""


def test_real_mode_requires_api_key() -> None:
    with pytest.raises(ValueError, match="SARVAM_API_KEY is required"):
        resolve_sarvam_config({"SARVAM_USE_MOCK": "false"})


def test_real_mode_uses_configured_key_and_base_url() -> None:
    config = resolve_sarvam_config(
        {
            "SARVAM_USE_MOCK": "false",
            "SARVAM_API_KEY": "sk_live_abc123",
            "SARVAM_API_BASE_URL": "https://api.sarvam.ai",
            "SARVAM_CHAT_MODEL": "sarvam-30b",
        }
    )

    assert config.use_mock is False
    assert config.api_key == "sk_live_abc123"
    assert config.base_url == DEFAULT_REAL_BASE_URL
    assert config.default_model == "sarvam-30b"


def test_use_mock_is_case_insensitive() -> None:
    assert resolve_sarvam_config({"SARVAM_USE_MOCK": "TRUE"}).use_mock is True
    assert resolve_sarvam_config({"SARVAM_USE_MOCK": "False", "SARVAM_API_KEY": "k"}).use_mock is False
