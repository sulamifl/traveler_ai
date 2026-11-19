"""TTS через edge-tts (Microsoft Edge).

Голос выбирается по языку через `DEFAULT_VOICES`. Можно переопределить
параметром `voice`. Модуль не требует ключей API.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .base import SynthesisResult

logger = logging.getLogger(__name__)

DEFAULT_VOICES: dict[str, str] = {
    "ru": "ru-RU-DmitryNeural",
    "en": "en-US-GuyNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
    "zh": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
}
FALLBACK_VOICE = "en-US-GuyNeural"


class TTSError(RuntimeError):
    """Ошибка синтеза речи."""


class EdgeTTSSynthesizer:
    """Синтез речи через `edge_tts.Communicate`.

    Пример:
        tts = EdgeTTSSynthesizer()
        res = tts.synthesize("Привет", "out.mp3", language="ru")
        print(res.audio_path)
    """

    def __init__(
        self,
        voices: Optional[dict[str, str]] = None,
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> None:
        self.voices = {**DEFAULT_VOICES, **(voices or {})}
        self.rate = rate
        self.volume = volume

    def _resolve_voice(self, language: str | None, voice: str | None) -> str:
        if voice:
            return voice
        if language:
            base = language.split("-")[0].lower()
            if base in self.voices:
                return self.voices[base]
        return FALLBACK_VOICE

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        language: str | None = None,
        voice: str | None = None,
    ) -> SynthesisResult:
        if not text or not text.strip():
            raise ValueError("Пустой текст для синтеза")

        try:
            import edge_tts  # локальный импорт: тесты могут мокать
        except ImportError as exc:  # pragma: no cover
            raise TTSError(
                "edge-tts не установлен. Установите: pip install edge-tts"
            ) from exc

        resolved_voice = self._resolve_voice(language, voice)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        async def _run() -> None:
            communicate = edge_tts.Communicate(
                text,
                resolved_voice,
                rate=self.rate,
                volume=self.volume,
            )
            await communicate.save(str(path))

        try:
            asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001
            raise TTSError(f"Ошибка синтеза речи: {exc}") from exc

        if not path.exists() or path.stat().st_size == 0:
            raise TTSError(f"Файл не создан или пуст: {path}")

        logger.info(
            "Синтез выполнен: voice=%s, символов=%s, файл=%s",
            resolved_voice,
            len(text),
            path,
        )
        return SynthesisResult(audio_path=path, voice=resolved_voice, text=text)
