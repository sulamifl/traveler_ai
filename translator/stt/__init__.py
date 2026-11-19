"""Модуль распознавания речи (STT)."""

from .base import Transcriber, TranscriptionResult, TranscriptionSegment
from .whisper_stt import WhisperTranscriber

__all__ = [
    "Transcriber",
    "TranscriptionResult",
    "TranscriptionSegment",
    "WhisperTranscriber",
]
