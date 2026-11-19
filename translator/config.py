"""Конфигурация приложения через переменные окружения.

Все настройки читаются из env с разумными дефолтами. Значения можно
переопределить аргументами CLI — они имеют приоритет над env.

Пример:
    cfg = Config.from_env()
    print(cfg.deepseek_api_key, cfg.whisper_model)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть целым числом, получено: {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть числом, получено: {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    """Настройки приложения.

    Все поля имеют дефолты, чтобы приложение запускалось «из коробки»
    (кроме `deepseek_api_key`, который нужен только для перевода).
    """

    # STT
    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "default"

    # Перевод
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: float = 30.0

    # TTS
    tts_rate: str = "+0%"
    tts_volume: str = "+0%"

    # Аудио
    audio_sample_rate: int = 16_000
    audio_channels: int = 1
    audio_dtype: str = "int16"

    # История
    history_db_path: str = "history.db"

    # Логирование
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Собрать конфиг из переменных окружения."""
        return cls(
            whisper_model=_env_str("WHISPER_MODEL", cls.whisper_model) or cls.whisper_model,
            whisper_device=_env_str("WHISPER_DEVICE", cls.whisper_device) or cls.whisper_device,
            whisper_compute_type=_env_str("WHISPER_COMPUTE_TYPE", cls.whisper_compute_type)
            or cls.whisper_compute_type,
            deepseek_api_key=_env_str("DEEPSEEK_API_KEY"),
            deepseek_base_url=_env_str("DEEPSEEK_BASE_URL", cls.deepseek_base_url)
            or cls.deepseek_base_url,
            deepseek_model=_env_str("DEEPSEEK_MODEL", cls.deepseek_model) or cls.deepseek_model,
            deepseek_timeout=_env_float("DEEPSEEK_TIMEOUT", cls.deepseek_timeout),
            tts_rate=_env_str("TTS_RATE", cls.tts_rate) or cls.tts_rate,
            tts_volume=_env_str("TTS_VOLUME", cls.tts_volume) or cls.tts_volume,
            audio_sample_rate=_env_int("AUDIO_SAMPLE_RATE", cls.audio_sample_rate),
            audio_channels=_env_int("AUDIO_CHANNELS", cls.audio_channels),
            audio_dtype=_env_str("AUDIO_DTYPE", cls.audio_dtype) or cls.audio_dtype,
            history_db_path=_env_str("HISTORY_DB_PATH", cls.history_db_path)
            or cls.history_db_path,
            log_level=(_env_str("LOG_LEVEL", cls.log_level) or cls.log_level).upper(),
        )
