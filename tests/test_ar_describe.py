"""Тесты описания/перевода OCR-блоков. Без реального OCR и сети."""

from __future__ import annotations

import numpy as np
import pytest

from translator.ar.describe import DescribeError, ObjectDescriber
from translator.ar.ocr import OCRBlock
from translator.translate.base import TranslationResult


class _FakeOCR:
    def __init__(self, blocks: list[OCRBlock]):
        self._blocks = blocks
        self.calls = 0

    def recognize(self, frame):  # noqa: ANN001
        self.calls += 1
        return list(self._blocks)


class _FakeTranslator:
    def __init__(self, fail_on: str | None = None):
        self.calls: list[tuple[str, str, str | None]] = []
        self._fail_on = fail_on

    def translate(self, text, target_lang, source_lang=None):
        self.calls.append((text, target_lang, source_lang))
        if self._fail_on is not None and text == self._fail_on:
            raise RuntimeError("boom")
        return TranslationResult(
            text=f"[{target_lang}] {text}",
            source_lang=source_lang,
            target_lang=target_lang,
        )


def _frame() -> np.ndarray:
    return np.zeros((10, 10, 3), dtype=np.uint8)


def _block(text: str, conf: float = 90.0, x: int = 0, y: int = 0) -> OCRBlock:
    return OCRBlock(
        text=text, confidence=conf, left=x, top=y, width=10, height=5
    )


def test_describe_translates_each_block():
    ocr = _FakeOCR([_block("Hello", x=1), _block("World", x=20)])
    tr = _FakeTranslator()
    describer = ObjectDescriber(ocr=ocr, translator=tr)

    result = describer.describe(_frame(), target_lang="ru", source_lang="en")

    assert len(result.blocks) == 2
    assert result.blocks[0].original_text == "Hello"
    assert result.blocks[0].translated_text == "[ru] Hello"
    assert result.blocks[0].bbox == (1, 0, 10, 5)
    assert result.blocks[1].translated_text == "[ru] World"
    assert result.combined_original == "Hello World"
    assert result.combined_translated == "[ru] Hello [ru] World"
    assert tr.calls == [
        ("Hello", "ru", "en"),
        ("World", "ru", "en"),
    ]


def test_describe_empty_frame_raises():
    describer = ObjectDescriber(ocr=_FakeOCR([]), translator=_FakeTranslator())
    with pytest.raises(DescribeError):
        describer.describe(None, target_lang="ru")


def test_describe_no_blocks_returns_empty():
    describer = ObjectDescriber(ocr=_FakeOCR([]), translator=_FakeTranslator())
    result = describer.describe(_frame(), target_lang="ru")
    assert result.blocks == []
    assert result.combined_original == ""
    assert result.combined_translated == ""


def test_describe_filters_by_min_confidence():
    ocr = _FakeOCR([_block("low", conf=10.0), _block("high", conf=90.0)])
    tr = _FakeTranslator()
    describer = ObjectDescriber(ocr=ocr, translator=tr, min_confidence=50.0)

    result = describer.describe(_frame(), target_lang="ru")
    assert [b.original_text for b in result.blocks] == ["high"]
    assert tr.calls == [("high", "ru", None)]


def test_describe_translation_error_wrapped():
    ocr = _FakeOCR([_block("bad")])
    tr = _FakeTranslator(fail_on="bad")
    describer = ObjectDescriber(ocr=ocr, translator=tr)
    with pytest.raises(DescribeError):
        describer.describe(_frame(), target_lang="ru")


def test_describe_invalid_target_lang():
    describer = ObjectDescriber(ocr=_FakeOCR([]), translator=_FakeTranslator())
    with pytest.raises(ValueError):
        describer.describe(_frame(), target_lang="")


def test_describe_invalid_min_confidence():
    with pytest.raises(ValueError):
        ObjectDescriber(ocr=_FakeOCR([]), translator=_FakeTranslator(), min_confidence=-1)
    with pytest.raises(ValueError):
        ObjectDescriber(ocr=_FakeOCR([]), translator=_FakeTranslator(), min_confidence=101)


def test_describe_uses_ocr_factory_with_source_lang():
    created: list[str] = []

    def ocr_factory(lang: str) -> _FakeOCR:
        created.append(lang)
        return _FakeOCR([_block("Hallo")])

    describer = ObjectDescriber(
        ocr_factory=ocr_factory,
        translator=_FakeTranslator(),
    )
    result = describer.describe(_frame(), target_lang="ru", source_lang="deu")

    assert created == ["deu"]
    assert result.blocks[0].original_text == "Hallo"


def test_describe_requires_ocr_or_factory():
    with pytest.raises(ValueError):
        ObjectDescriber(translator=_FakeTranslator())


def test_describe_requires_translator():
    with pytest.raises(ValueError):
        ObjectDescriber(ocr=_FakeOCR([]))
