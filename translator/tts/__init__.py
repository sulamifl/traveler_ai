"""Модуль синтеза речи (TTS)."""

from .base import SynthesisResult, Synthesizer
from .edge_tts import EdgeTTSSynthesizer, TTSError

__all__ = [
    "SynthesisResult",
    "Synthesizer",
    "EdgeTTSSynthesizer",
    "TTSError",
]
