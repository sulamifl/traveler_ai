"""Интерфейсы для модуля TTS.

Все реализации синтезатора возвращают `SynthesisResult`,
чтобы пайплайн не зависел от конкретной библиотеки.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SynthesisResult:
    """Результат синтеза речи."""

    audio_path: Path
    voice: str
    text: str


@runtime_checkable
class Synthesizer(Protocol):
    """Протокол любого TTS-движка."""

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        language: str | None = None,
        voice: str | None = None,
    ) -> SynthesisResult:
        """Синтезировать речь в аудиофайл."""
        ...
