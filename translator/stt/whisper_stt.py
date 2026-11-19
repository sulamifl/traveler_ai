"""STT через faster-whisper.

Модель загружается лениво при первом вызове `transcribe`, чтобы импорт
модуля не тянул веса и не требовал GPU.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from .base import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)

DEFAULT_MODEL_SIZE = "small"


class WhisperTranscriber:
    """Обёртка над `faster_whisper.WhisperModel`.

    Пример:
        stt = WhisperTranscriber(model_size="small")
        result = stt.transcribe("audio.wav", language="ru")
        print(result.text)
    """

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL_SIZE,
        device: str = "auto",
        compute_type: str = "default",
        model: Optional[Any] = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = model

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel  # локальный импорт
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "faster-whisper не установлен. Установите: pip install faster-whisper"
            ) from exc

        logger.info(
            "Загрузка Whisper: size=%s, device=%s, compute_type=%s",
            self.model_size,
            self.device,
            self.compute_type,
        )
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        return self._model

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
    ) -> TranscriptionResult:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Аудиофайл не найден: {path}")

        model = self._ensure_model()
        segments_iter, info = model.transcribe(
            str(path),
            language=language,
            beam_size=5,
        )

        segments: list[TranscriptionSegment] = []
        texts: list[str] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            segments.append(
                TranscriptionSegment(
                    start=float(seg.start),
                    end=float(seg.end),
                    text=text,
                )
            )
            texts.append(text)

        detected_lang = getattr(info, "language", None)
        full_text = " ".join(texts).strip()
        logger.info(
            "Распознано: lang=%s, сегментов=%s, символов=%s",
            detected_lang,
            len(segments),
            len(full_text),
        )
        return TranscriptionResult(
            text=full_text,
            language=detected_lang,
            segments=segments,
        )
