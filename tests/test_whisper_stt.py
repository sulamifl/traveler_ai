"""Тесты для WhisperTranscriber. Не требуют faster-whisper и весов."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from translator.stt.base import Transcriber
from translator.stt.whisper_stt import WhisperTranscriber


class _FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


class _FakeModel:
    def __init__(self, segments, language="ru"):
        self._segments = segments
        self._language = language
        self.calls: list[dict] = []

    def transcribe(self, path, language=None, beam_size=5):
        self.calls.append({"path": path, "language": language, "beam_size": beam_size})
        info = SimpleNamespace(language=self._language)
        return iter(self._segments), info


def test_transcribe_returns_result(tmp_path: Path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")

    model = _FakeModel(
        [
            _FakeSegment(0.0, 1.0, " привет "),
            _FakeSegment(1.0, 2.0, "мир"),
            _FakeSegment(2.0, 3.0, "   "),  # пустой — должен отфильтроваться
        ]
    )
    stt = WhisperTranscriber(model=model)

    result = stt.transcribe(audio, language="ru")

    assert result.text == "привет мир"
    assert result.language == "ru"
    assert len(result.segments) == 2
    assert result.segments[0].text == "привет"
    assert model.calls[0]["language"] == "ru"
    assert model.calls[0]["beam_size"] == 5


def test_transcribe_missing_file_raises(tmp_path: Path):
    stt = WhisperTranscriber(model=_FakeModel([]))
    with pytest.raises(FileNotFoundError):
        stt.transcribe(tmp_path / "nope.wav")


def test_implements_protocol():
    stt = WhisperTranscriber(model=_FakeModel([]))
    assert isinstance(stt, Transcriber)
