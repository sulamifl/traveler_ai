"""STT через Groq Whisper API.

Groq предоставляет OpenAI-совместимый эндпоинт `/audio/transcriptions`
с моделями `whisper-large-v3-turbo` и `whisper-large-v3`. Бесплатный tier
позволяет не тратить RAM сервера на локальную модель.

Пример:
    stt = GroqTranscriber(api_key="gsk_...")
    result = stt.transcribe("audio.webm", language="ru")
    print(result.text)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .base import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "whisper-large-v3-turbo"
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_TIMEOUT = 60.0


class GroqSTTError(RuntimeError):
    """Ошибка распознавания речи через Groq."""


class GroqTranscriber:
    """Обёртка над Groq `/audio/transcriptions`.

    Реализует протокол `Transcriber`.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[object] = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError(
                "Не задан GROQ_API_KEY. Получите бесплатный ключ на console.groq.com"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from groq import Groq  # локальный импорт: тесты могут мокать
        except ImportError as exc:  # pragma: no cover
            raise GroqSTTError(
                "groq не установлен. Установите: pip install groq"
            ) from exc
        self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
    ) -> TranscriptionResult:
        path = Path(audio_path)
        if not path.exists():
            raise GroqSTTError(f"Файл не найден: {path}")

        client = self._get_client()
        try:
            with path.open("rb") as fh:
                kwargs: dict = {
                    "file": (path.name, fh.read()),
                    "model": self.model,
                    "response_format": "verbose_json",
                }
                if language:
                    kwargs["language"] = language
                response = client.audio.transcriptions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise GroqSTTError(f"Ошибка Groq STT: {exc}") from exc

        text = getattr(response, "text", "") or ""
        detected_lang = getattr(response, "language", None) or language

        segments: list[TranscriptionSegment] = []
        raw_segments = getattr(response, "segments", None) or []
        for seg in raw_segments:
            if isinstance(seg, dict):
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
                seg_text = seg.get("text", "")
            else:
                start = float(getattr(seg, "start", 0.0))
                end = float(getattr(seg, "end", 0.0))
                seg_text = getattr(seg, "text", "")
            segments.append(
                TranscriptionSegment(start=start, end=end, text=seg_text)
            )

        logger.info(
            "Groq STT: model=%s, lang=%s, len=%s",
            self.model,
            detected_lang,
            len(text),
        )
        return TranscriptionResult(
            text=text,
            language=detected_lang,
            segments=segments,
        )
