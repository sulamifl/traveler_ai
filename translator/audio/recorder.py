"""Запись аудио с микрофона в WAV-файл.

Модуль намеренно не зависит от STT/TTS — только захват звука.
Использует `sounddevice` (PortAudio) и `numpy`.
"""

from __future__ import annotations

import logging
import wave
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_CHANNELS = 1
DEFAULT_DTYPE = "int16"


class AudioRecorderError(RuntimeError):
    """Ошибка при записи аудио."""


class AudioRecorder:
    """Записывает аудио с микрофона в WAV.

    Пример:
        rec = AudioRecorder()
        rec.start()
        ...
        path = rec.stop()  # -> Path к .wav
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        dtype: str = DEFAULT_DTYPE,
        device: Optional[int] = None,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate должен быть > 0")
        if channels <= 0:
            raise ValueError("channels должен быть > 0")

        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.device = device

        self._frames: list[np.ndarray] = []
        self._stream = None
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        """Начать запись. Бросает AudioRecorderError при проблемах с устройством."""
        if self._recording:
            raise AudioRecorderError("Запись уже идёт")

        try:
            import sounddevice as sd  # локальный импорт: тесты могут мокать
        except ImportError as exc:  # pragma: no cover - зависит от окружения
            raise AudioRecorderError(
                "sounddevice не установлен. Установите: pip install sounddevice"
            ) from exc

        self._frames = []

        def _callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                logger.warning("sounddevice status: %s", status)
            # копия, т.к. буфер переиспользуется
            self._frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                device=self.device,
                callback=_callback,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            self._stream = None
            raise AudioRecorderError(f"Не удалось открыть микрофон: {exc}") from exc

        self._recording = True
        logger.info(
            "Запись начата: rate=%s, channels=%s, dtype=%s",
            self.sample_rate,
            self.channels,
            self.dtype,
        )

    def stop(self, output_path: str | Path) -> Path:
        """Остановить запись и сохранить в WAV. Возвращает путь к файлу."""
        if not self._recording:
            raise AudioRecorderError("Запись не запущена")

        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            self._recording = False

        if not self._frames:
            raise AudioRecorderError("Не записано ни одного фрейма")

        audio = np.concatenate(self._frames, axis=0)
        self._frames = []

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_wav(path, audio)
        logger.info("Запись сохранена: %s (%s сэмплов)", path, len(audio))
        return path

    def _write_wav(self, path: Path, audio: np.ndarray) -> None:
        sample_width = np.dtype(self.dtype).itemsize
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())
