"""Тесты конфигурации и логирования."""

from __future__ import annotations

import logging

import pytest

from translator.config import Config
from translator.logging_setup import setup_logging


def test_defaults(monkeypatch):
    for name in (
        "WHISPER_MODEL",
        "WHISPER_DEVICE",
        "WHISPER_COMPUTE_TYPE",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_TIMEOUT",
        "TTS_RATE",
        "TTS_VOLUME",
        "AUDIO_SAMPLE_RATE",
        "AUDIO_CHANNELS",
        "AUDIO_DTYPE",
        "HISTORY_DB_PATH",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)

    cfg = Config.from_env()
    assert cfg.whisper_model == "small"
    assert cfg.deepseek_api_key is None
    assert cfg.audio_sample_rate == 16_000
    assert cfg.audio_channels == 1
    assert cfg.history_db_path == "history.db"
    assert cfg.log_level == "INFO"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL", "medium")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("AUDIO_SAMPLE_RATE", "8000")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT", "5.5")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    cfg = Config.from_env()
    assert cfg.whisper_model == "medium"
    assert cfg.deepseek_api_key == "sk-test"
    assert cfg.audio_sample_rate == 8000
    assert cfg.deepseek_timeout == 5.5
    assert cfg.log_level == "DEBUG"


def test_invalid_int_raises(monkeypatch):
    monkeypatch.setenv("AUDIO_SAMPLE_RATE", "not-a-number")
    with pytest.raises(ValueError):
        Config.from_env()


def test_invalid_float_raises(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_TIMEOUT", "abc")
    with pytest.raises(ValueError):
        Config.from_env()


def test_setup_logging_sets_level():
    setup_logging("WARNING")
    assert logging.getLogger().level == logging.WARNING
    setup_logging("INFO")
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_idempotent():
    setup_logging("INFO")
    setup_logging("INFO")
    handlers = [
        h for h in logging.getLogger().handlers
        if getattr(h, "_translator_handler", False)
    ]
    assert len(handlers) == 1


def test_setup_logging_invalid_level():
    with pytest.raises(ValueError):
        setup_logging("NOPE")
