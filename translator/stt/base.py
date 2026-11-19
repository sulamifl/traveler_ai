"""Интерфейсы для модуля STT.

Все реализации STT должны возвращать `TranscriptionResult`,
чтобы остальной пайплайн не зависел от конкретной библиотеки.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TranscriptionSegment:
    """Один сегмент распознанной речи."""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Результат распознавания аудиофайла."""

    text: str
    language: str | None = None
    segments: list[TranscriptionSegment] = field(default_factory=list)


@runtime_checkable
class Transcriber(Protocol):
    """Протокол любого STT-движка."""

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Распознать речь в аудиофайле."""
        ...
