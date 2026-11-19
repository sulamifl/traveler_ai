"""Тесты для EdgeTTSSynthesizer. Не требуют edge-tts и сети."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from translator.tts.base import Synthesizer
from translator.tts.edge_tts import EdgeTTSSynthesizer, TTSError


class _FakeCommunicate:
    def __init__(self, text, voice, rate="+0%", volume="+0%"):
        self.text = text
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.saved_to: str | None = None

    async def save(self, path: str) -> None:
        self.saved_to = path
        Path(path).write_bytes(b"FAKE_MP3")


@pytest.fixture
def fake_edge_tts(monkeypatch):
    module = types.ModuleType("edge_tts")
    module.Communicate = _FakeCommunicate
    monkeypatch.setitem(sys.modules, "edge_tts", module)
    return module


def test_synthesize_creates_file(tmp_path: Path, fake_edge_tts):
    tts = EdgeTTSSynthesizer()
    out = tmp_path / "out.mp3"

    res = tts.synthesize("Привет", out, language="ru")

    assert out.exists()
    assert out.read_bytes() == b"FAKE_MP3"
    assert res.audio_path == out
    assert res.voice == "ru-RU-DmitryNeural"
    assert res.text == "Привет"


def test_voice_override(tmp_path: Path, fake_edge_tts):
    tts = EdgeTTSSynthesizer()
    res = tts.synthesize("Hi", tmp_path / "a.mp3", voice="en-GB-SoniaNeural")
    assert res.voice == "en-GB-SoniaNeural"


def test_unknown_language_uses_fallback(tmp_path: Path, fake_edge_tts):
    tts = EdgeTTSSynthesizer()
    res = tts.synthesize("X", tmp_path / "a.mp3", language="xx")
    assert res.voice == "en-US-GuyNeural"


def test_empty_text_raises(tmp_path: Path):
    tts = EdgeTTSSynthesizer()
    with pytest.raises(ValueError):
        tts.synthesize("   ", tmp_path / "a.mp3")


def test_missing_edge_tts_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "edge_tts", None)
    tts = EdgeTTSSynthesizer()
    with pytest.raises(TTSError):
        tts.synthesize("Привет", tmp_path / "a.mp3", language="ru")


def test_implements_protocol():
    tts = EdgeTTSSynthesizer()
    assert isinstance(tts, Synthesizer)
