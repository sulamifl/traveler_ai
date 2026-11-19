"""Тесты для AudioRecorder. Не требуют реального микрофона."""

from __future__ import annotations

import sys
import types
import wave
from pathlib import Path

import numpy as np
import pytest

from translator.audio.recorder import AudioRecorder, AudioRecorderError


class _FakeStream:
    def __init__(self, callback, **kwargs):
        self._callback = callback
        self._kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True
        # эмулируем 3 фрейма по 160 сэмплов
        for _ in range(3):
            buf = np.zeros((160, self._kwargs["channels"]), dtype=np.int16)
            self._callback(buf, 160, None, None)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


@pytest.fixture
def fake_sounddevice(monkeypatch):
    module = types.ModuleType("sounddevice")

    def InputStream(**kwargs):
        return _FakeStream(kwargs.pop("callback"), **kwargs)

    module.InputStream = InputStream
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    return module


def test_records_and_writes_wav(tmp_path: Path, fake_sounddevice):
    rec = AudioRecorder(sample_rate=16_000, channels=1)
    rec.start()
    assert rec.is_recording

    out = rec.stop(tmp_path / "out.wav")
    assert out.exists()
    assert not rec.is_recording

    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16_000
        assert wf.getsampwidth() == 2
        assert wf.getnframes() == 3 * 160


def test_stop_without_start_raises(tmp_path: Path):
    rec = AudioRecorder()
    with pytest.raises(AudioRecorderError):
        rec.stop(tmp_path / "x.wav")


def test_double_start_raises(fake_sounddevice):
    rec = AudioRecorder()
    rec.start()
    with pytest.raises(AudioRecorderError):
        rec.start()
    rec.stop(Path("dummy.wav"))


def test_invalid_params():
    with pytest.raises(ValueError):
        AudioRecorder(sample_rate=0)
    with pytest.raises(ValueError):
        AudioRecorder(channels=0)
