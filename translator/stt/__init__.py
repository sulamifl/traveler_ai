"""Модуль распознавания речи (STT)."""

from .base import Transcriber, TranscriptionResult, TranscriptionSegment
from .groq_stt import GroqSTTError, GroqTranscriber

__all__ = [
    "Transcriber",
    "TranscriptionResult",
    "TranscriptionSegment",
    "GroqSTTError",
    "GroqTranscriber",
]
