"""Тесты OCR. Tesseract не требуется — используется мок pytesseract."""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from translator.ar.ocr import OCR, OCRError


class _FakeOutput:
    DICT = "dict"


def _make_fake_pytesseract(data: dict) -> types.ModuleType:
    module = types.ModuleType("pytesseract")
    module.Output = _FakeOutput
    module.pytesseract = types.SimpleNamespace(tesseract_cmd="")

    def image_to_data(frame, lang=None, output_type=None):
        return data

    module.image_to_data = image_to_data
    return module


def _frame() -> np.ndarray:
    return np.zeros((10, 10, 3), dtype=np.uint8)


def test_recognize_returns_blocks(monkeypatch):
    data = {
        "text": ["", "Hello", "World", "low"],
        "conf": ["-1", "95.5", "80", "10"],
        "left": [0, 1, 2, 3],
        "top": [0, 4, 5, 6],
        "width": [0, 10, 20, 30],
        "height": [0, 5, 6, 7],
    }
    monkeypatch.setitem(sys.modules, "pytesseract", _make_fake_pytesseract(data))

    ocr = OCR(lang="eng", min_confidence=40.0)
    blocks = ocr.recognize(_frame())

    assert len(blocks) == 2
    assert blocks[0].text == "Hello"
    assert blocks[0].confidence == 95.5
    assert blocks[0].bbox == (1, 4, 10, 5)
    assert blocks[1].text == "World"


def test_recognize_empty_frame_raises():
    ocr = OCR()
    with pytest.raises(OCRError):
        ocr.recognize(None)


def test_invalid_lang():
    with pytest.raises(ValueError):
        OCR(lang="")


def test_invalid_min_confidence():
    with pytest.raises(ValueError):
        OCR(min_confidence=-1)
    with pytest.raises(ValueError):
        OCR(min_confidence=101)


def test_missing_pytesseract_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pytesseract":
            raise ImportError("no pytesseract")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    ocr = OCR()
    with pytest.raises(OCRError):
        ocr.recognize(_frame())


def test_tesseract_cmd_applied(monkeypatch):
    data = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    fake = _make_fake_pytesseract(data)
    monkeypatch.setitem(sys.modules, "pytesseract", fake)

    ocr = OCR(tesseract_cmd="/custom/tesseract")
    ocr.recognize(_frame())
    assert fake.pytesseract.tesseract_cmd == "/custom/tesseract"
