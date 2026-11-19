"""Тесты для TranslationPipeline с фейковыми компонентами."""

from __future__ import annotations

from pathlib import Path

import pytest

from translator.pipeline import TranslationPipeline
from translator.stt.base import TranscriptionResult, TranscriptionSegment
from translator.translate.base import TranslationResult
from translator.tts.base import SynthesisResult


class _FakeSTT:
    def __init__(self, text: str, language: str | None = "ru"):
        self._text = text
        self._language = language
        self.calls: list[dict] = []

    def transcribe(self, audio_path, language=None):
        self.calls.append({"audio_path": audio_path, "language": language})
        return TranscriptionResult(
            text=self._text,
            language=self._language,
            segments=[TranscriptionSegment(0.0, 1.0, self._text)],
        )


class _FakeTranslator:
    def __init__(self, text: str = "Hello"):
        self._text = text
        self.calls: list[dict] = []

    def translate(self, text, target_lang, source_lang=None):
        self.calls.append(
            {"text": text, "target_lang": target_lang, "source_lang": source_lang}
        )
        return TranslationResult(
            text=self._text, source_lang=source_lang, target_lang=target_lang
        )


class _FakeTTS:
    def __init__(self):
        self.calls: list[dict] = []

    def synthesize(self, text, output_path, language=None, voice=None):
        self.calls.append(
            {"text": text, "output_path": output_path, "language": language}
        )
        return SynthesisResult(
            audio_path=Path(output_path), voice="fake", text=text
        )


def test_pipeline_without_tts(tmp_path: Path):
    stt = _FakeSTT("Привет")
    tr = _FakeTranslator("Hello")
    pipe = TranslationPipeline(stt=stt, translator=tr)

    res = pipe.run(tmp_path / "a.wav", target_lang="en")

    assert res.transcription.text == "Привет"
    assert res.translation.text == "Hello"
    assert res.synthesis is None
    assert tr.calls[0]["source_lang"] == "ru"  # из STT


def test_pipeline_with_tts(tmp_path: Path):
    stt = _FakeSTT("Привет")
    tr = _FakeTranslator("Hello")
    tts = _FakeTTS()
    pipe = TranslationPipeline(stt=stt, translator=tr, tts=tts)

    out = tmp_path / "out.mp3"
    res = pipe.run(tmp_path / "a.wav", target_lang="en", tts_output=out)

    assert res.synthesis is not None
    assert res.synthesis.audio_path == out
    assert tts.calls[0]["text"] == "Hello"
    assert tts.calls[0]["language"] == "en"


def test_pipeline_empty_transcription_raises(tmp_path: Path):
    stt = _FakeSTT("")
    tr = _FakeTranslator()
    pipe = TranslationPipeline(stt=stt, translator=tr)
    with pytest.raises(RuntimeError):
        pipe.run(tmp_path / "a.wav", target_lang="en")
